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
an `a`-prefixed async flavour: `declare_streams`, `publisher_connection`, `watch_stream`,
`watch_agent`, `get_stream`, `is_stream_live`, `list_streams`, `get_agent`, ….

### Publishing streams

`lovekit.publish(...)` declares an app's streams and keeps them published:

```python
from lovekit import VideoStream, to_rgba

async with lovekit.publish([VideoStream("camera", title="Main camera")]) as live:
    print(live.streams)  # the declared streams (@lovekit/stream)
    while True:
        await live.video("camera").send(to_rgba(frame))  # (height, width, 4) uint8
```

- **The declaration is the app's whole set.** A stream keeps its id over restarts
  (it is found by its key), one the app no longer names is removed, and a restart
  that declares the same changes nothing. So a client publishes once at a time.
- **Every stream is a track named by its key**, carried by the transport lovekit names
  (today LiveKit: the agent's room). A video track is made on the first frame and again
  when the frame size changes; the last frame is sent again while no new one comes, so a
  late viewer sees a picture.
- **It stays live.** When the connection drops it is joined again (a fresh one, backoff)
  and every track published again. When another process of the same agent connects, or
  the participant is removed, this one stops for good (`live.stopped`,
  `await live.wait_stopped()`) instead of taking the room back.
- **Audio** is an `AudioStream("microphone")`, sent int16 samples.

### Data streams

A data stream carries small arrays that change fast: a spectrum, a trace, a profile.

```python
from lovekit import Axis, AxisType, Calibration, DataStream

spectrum = DataStream(
    "spectrum",
    dtype="float16",
    shape=(512,),
    axes=[Axis("wavelength", AxisType.SPECTRUM)],
    calibration=[Calibration("wavelength", unit="nm", scale=0.78, offset=400.0)],
    unit="counts",
)

async with lovekit.publish([spectrum]) as live:
    feed = live.data("spectrum")
    while True:
        await feed.wait_watched()  # nobody watching: nothing to measure
        await feed.send(read().astype("float16"))
```

- **A frame is one array of the declared dtype and shape, at most 1024 bytes**
  (512 float16 values, 256 float32). Decimate to what a plot shows; keep the full
  measurement elsewhere.
- **It is lossy and holds one value.** `send` never queues: a frame is sent, or it is
  the one that waits (for `max_rate`, or for the connection), and a newer one replaces it.
- **The axes are named as mikro's coordinate systems name theirs** (name and semantic
  type); what an axis measures is its `Calibration`, and `reference` names the space,
  so a stored spectrum of the same reference is in the same one.
- **`watched`** is never false while someone watches; it may be true when nobody does.

### In an arkitekt app

The client is injected by annotation. Hold the streams in a state, so the UI
shows them (in a blok: `<foreach items="@self.Live.streams" let="#stream">`
`<StructureDisplay value="@stream" /></foreach>`), and publish from a background
hook:

```python
from dataclasses import dataclass, field

from arkitekt import App, run
from lovekit import Lovekit, VideoStream, to_rgba
from lovekit.api.schema import Stream

app = App("camera", "0.1.0")


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

An app reads a data stream another app publishes with `lovekit.watch`:

```python
async with lovekit.watch(stream) as frames:
    async for frame in frames:
        plot(frame.values)  # an array as the stream declared it
```

It joins through whatever carries the stream, also over the mesh, and holds one value: a
reader slower than the stream skips frames. The frames end when the stream goes away.

Underneath, `watch_stream(stream)` and `watch_agent(agent)` return a connection (its
transport and a credential) that may subscribe to the agent's streams, but not publish;
the stream is the track named by its `key`.
`is_stream_live(stream)` says whether it is published right now.

## Development

The generated API (`lovekit/api/schema.py`) comes from the documents in
`graphql/`; see `graphql.config.yaml`.

```sh
uv run pytest -m "not integration"   # no server needed
uv run pytest -m integration          # a real lovekit + livekit via dokker
```

See [RELEASING.md](RELEASING.md) for how versions are cut.
