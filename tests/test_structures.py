"""A plain import declares the client and the types it sends by id."""

from arkitekt_spec.declare.client import client_of

from lovekit import Lovekit


def test_lovekit_declares_its_client_and_structures() -> None:
    declaration = client_of(Lovekit)
    assert declaration is not None and declaration.name == "lovekit"
    assert {s.identifier for s in declaration.structures} == {
        "@lovekit/agent",
        "@lovekit/stream",
    }
