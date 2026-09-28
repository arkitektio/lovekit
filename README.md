# lovekit

[![PyPI version](https://badge.fury.io/py/lovekit.svg)](https://pypi.org/project/lovekit/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/lovekit.svg)](https://pypi.python.org/pypi/lovekit/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)

The python client for lovekit, the [Arkitekt](https://arkitekt.live) service for
live audio and video. Lovekit manages broadcasts and their streams and hands out
the tokens to publish into them; the media itself flows over WebRTC through a
[LiveKit](https://livekit.io) media server, which you talk to with the regular
`livekit` SDK.

## Installation

```sh
pip install lovekit   # or: pip install "arkitekt[rekuest,lovekit]"
```

## Usage

Every lovekit operation is a method of the `Lovekit` client, in a blocking and
an `a`-prefixed async flavour: `ensure_solo_broadcast`, `ensure_stream`,
`get_stream`, `list_streams`, `get_solo_broadcast`, `list_solo_broadcasts`, ….
`ensure_stream` returns the token a `livekit.rtc.Room` connects to the media
server with.

### In an arkitekt app

The client is injected by annotation. Add the service to your app and ask for
`lovekit: Lovekit`:

```python
from arkitekt import App, run
from lovekit import lovekit_service
from lovekit.api.schema import StreamKind
from lovekit.lovekit import Lovekit

app = App("camera", "0.1.0", services=[lovekit_service])


@app.action
async def go_live(title: str, lovekit: Lovekit) -> str:
    """Go Live

    Opens a video stream and returns the token to publish into it.
    """
    broadcast = await lovekit.aensure_solo_broadcast(title=title)
    return await lovekit.aensure_stream(kind=StreamKind.VIDEO, broadcast=broadcast.id, title=title)


if __name__ == "__main__":
    run(app)
```

Streams and solo broadcasts travel between actions by id (`@lovekit/stream`,
`@lovekit/solo_broadcast`), so an action can take and return them directly.

### From a script

```python
from arkitekt import easy
from lovekit import lovekit_service

with easy("my-script", lovekit_service) as lovekit:
    for stream in lovekit.list_streams():
        print(stream.id)
```

With a token, publish or subscribe through the regular `livekit` SDK
(`await rtc.Room().connect(<livekit url>, token)`).

## Development

The generated API (`lovekit/api/schema.py`) comes from the documents in
`graphql/`; see `graphql.config.yaml`.

```sh
uv run pytest -m "not integration"   # no server needed
uv run pytest -m integration          # a real lovekit + livekit via dokker
```

See [RELEASING.md](RELEASING.md) for how versions are cut.
