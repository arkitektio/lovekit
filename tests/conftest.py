import sys
import pytest
from dokker import Deployment, testing
from dokker.log_watcher import LogWatcher
import os
import socket
from typing import Generator
from lovekit.lovekit import Lovekit
from rath.links.auth import ComposedAuthLink
from rath.links.aiohttp import AIOHttpLink
from rath.links.graphql_ws import GraphQLWSLink
from rath.links.timeout import TimeoutLink
from rath.links.compose import compose
from lovekit.rath import (
    LovekitRath,
    SplitLink,
)
from graphql import OperationType
from dataclasses import dataclass


def pytest_configure(config: pytest.Config) -> None:
    """Register custom platform markers."""
    config.addinivalue_line("markers", "linux_only: skip on non-Linux platforms")
    config.addinivalue_line("markers", "no_windows: skip on Windows")


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:  # noqa: ARG001
    """Skip tests marked linux_only or no_windows on the wrong platform."""
    for item in items:
        if item.get_closest_marker("linux_only") and sys.platform != "linux":
            item.add_marker(pytest.mark.skip(reason="Linux only"))
        if item.get_closest_marker("no_windows") and sys.platform == "win32":
            item.add_marker(pytest.mark.skip(reason="Not supported on Windows"))


project_path = os.path.join(os.path.dirname(__file__), "integration")
docker_compose_file = os.path.join(project_path, "docker-compose.yml")


def _reserve_free_ports(count: int) -> list[int]:
    """Ask the OS for `count` distinct free TCP ports.

    All sockets are held open until every port has been assigned, so the kernel
    cannot hand out the same port twice within one call. They are released
    before compose binds them -- a race in theory, but the ephemeral range is
    large and this is what keeps concurrent runs (and the leftovers of a crashed
    one) from colliding on a fixed port.
    """
    sockets: list[socket.socket] = []
    try:
        for _ in range(count):
            sock = socket.socket()
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
        return [int(sock.getsockname()[1]) for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


@pytest.fixture(scope="session")
def integration_ports() -> Generator[dict[str, int], None, None]:
    """Pick this run's host ports and point compose at them.

    Reserved rather than left to docker (`ports: - "80"`) because
    `Deployment.spec` is rendered by `docker compose config`, which is static:
    an unpublished port reads back as ``None`` and the test URLs would quietly
    become ``http://localhost:None`` instead of failing loudly.
    """
    lovekit_port, minio_port = _reserve_free_ports(2)
    env = {"LOVEKIT_HOST_PORT": str(lovekit_port), "MINIO_HOST_PORT": str(minio_port)}
    previous = {key: os.environ.get(key) for key in env}
    os.environ.update(env)
    try:
        yield {"lovekit": lovekit_port, "minio": minio_port}
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def token_loader() -> str:
    """Load a static token that is defined in the lovekit.yaml config file."""
    return "test"


@dataclass
class DeployedLovekit:
    """A deployed Lovekit instance backed by the dokker docker-compose stack."""

    deployment: Deployment
    lovekit_watcher: LogWatcher
    lovekit: Lovekit


@pytest.fixture(scope="session")
def deployed_app(integration_ports: dict[str, int]) -> Generator[DeployedLovekit, None, None]:
    """Deploy the Lovekit service via docker-compose and yield a connected client."""
    # testing(): a per-run `dokker-test-<hash>` project that is torn down on
    # exit, so concurrent or crashed runs (and sibling repos, which all name
    # their stack `integration`) never share containers.
    setup = testing(docker_compose_file)
    setup.add_health_check(
        url=lambda spec: f"http://localhost:{spec.find_service('lovekit').get_port_for_internal(80).published}/graphql",
        service="lovekit",
        timeout=5,
        # dokker sleeps `timeout` seconds between attempts: 20 x 5 s covers a
        # cold backend on a two-core runner, where 10 did not.
        max_retries=20,
    )

    watcher = setup.create_watcher("lovekit")

    with setup:
        setup.down()
        setup.pull()
        setup.inspect()

        http_url = f"http://localhost:{setup.spec.find_service('lovekit').get_port_for_internal(80).published}/graphql"
        ws_url = f"ws://localhost:{setup.spec.find_service('lovekit').get_port_for_internal(80).published}/graphql"

        print(f"HTTP URL: {http_url}")
        print(f"WS URL: {ws_url}")

        rath = LovekitRath(
            link=compose(
                TimeoutLink(timeout=12),
                ComposedAuthLink(
                    token_loader=token_loader, token_refresher=token_loader
                ),
                SplitLink(
                    left=AIOHttpLink(endpoint_url=http_url),
                    right=GraphQLWSLink(ws_endpoint_url=ws_url),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            ),
        )

        lovekit = Lovekit(rath=rath)

        setup.up()

        setup.run("initc", command="python init.py")

        setup.check_health()

        with lovekit as lovekit:
            yield DeployedLovekit(
                deployment=setup,
                lovekit_watcher=watcher,
                lovekit=lovekit,
            )
