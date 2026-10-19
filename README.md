# lovekit

[![PyPI version](https://badge.fury.io/py/lovekit.svg)](https://pypi.org/project/lovekit/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/lovekit.svg)](https://pypi.python.org/pypi/lovekit/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)

The python client for lovekit, the [Arkitekt](https://arkitekt.live) service for
live audio and video. An app (an *agent*: one client, user and organization)
declares the live sources it offers, its *streams*, and lovekit keeps them, hands
out the tokens to publish and watch them, and says which are live. The media
itself flows over WebRTC through a [LiveKit](https://livekit.io) media server.

## Installation

```sh
pip install lovekit   # or: pip install "arkitekt[rekuest,lovekit]"
```

## Usage

Every lovekit operation is a method of the `Lovekit` client, in a blocking and
an `a`-prefixed async flavour: `declare_streams`, `publish_token`, `watch_stream`,
`watch_agent`, `get_stream`, `is_stream_live`, `list_streams`, `get_agent`, ….

### Publishing streams

`lovekit.publish(...)` declares an app's streams and keeps them published:

```python
from lovekit import VideoStream, to_rgba

async with lovekit.publish([VideoStream("camera", title="Main camera")]) as live:
    print(live.streams)                          # the declared streams (@lovekit/stream)
    while True:
        await live["camera"].send(to_rgba(frame))  # (height, width, 4) uint8
```

- **The declaration is the app's whole set.** A stream keeps its id over restarts
  (it is found by its key), one the app no longer names is removed, and a restart
  that declares the same changes nothing. So a client publishes once at a time.
- **Every stream is a track of the agent's LiveKit room, named by its key.** A track
  is made on the first frame and again when the frame size changes; the last frame
  is sent again while no new one comes, so a late viewer sees a picture.
- **It stays live.** When the room drops it is joined again (fresh token, backoff) and
  every track published again. When another process of the same agent connects, or
  the participant is removed, this one stops for good (`live.stopped`,
  `await live.wait_stopped()`) instead of taking the room back.
- **Audio** is an `AudioStream("microphone")`, sent int16 samples.

### In an arkitekt app

The client is injected by annotation. Hold the streams in a state, so the UI
shows them (in a blok: `<foreach items="@self.Live.streams" let="#stream">`
`<StructureDisplay value="@stream" /></foreach>`), and publish from a background
hook:

```python
from dataclasses import dataclass, field

from arkitekt import App, run
from lovekit import VideoStream, lovekit_service, to_rgba
from lovekit.api.schema import Stream
from lovekit.lovekit import Lovekit

app = App("camera", "0.1.0", services=[lovekit_service])


@app.state
@dataclass
class Live:
    streams: list[Stream] = field(default_factory=list)


@app.startup
def no_streams_yet() -> Live:
    """Every state starts from a startup hook: empty, until the streams are declared."""
    return Live()


@app.background
async def stream_camera(lovekit: Lovekit, live: Live) -> None:
    async with lovekit.publish([VideoStream("camera")]) as published:
        live.streams = list(published.streams)
        while not published.stopped.is_set():
            await published["camera"].send(to_rgba(grab_frame()))


if __name__ == "__main__":
    run(app)
```

Streams and agents travel between actions by id (`@lovekit/stream`,
`@lovekit/agent`), so an action can take and return them directly.

### Watching

`watch_stream(stream)` and `watch_agent(agent)` return a token that may subscribe in
the agent's room, but not publish; the stream is the track named by its `key`.
`is_stream_live(stream)` says whether it is published right now.

## Development

The generated API (`lovekit/api/schema.py`) comes from the documents in
`graphql/`; see `graphql.config.yaml`.

```sh
uv run pytest -m "not integration"   # no server needed
uv run pytest -m integration          # a real lovekit + livekit via dokker
```

See [RELEASING.md](RELEASING.md) for how versions are cut.
