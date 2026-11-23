"""What a video track takes: RGBA uint8 frames, made from what cameras and detectors give."""

import numpy as np
import pytest

from lovekit import Axis, AxisType, DataStream, frames, to_rgba


def detector_frame(height: int = 8, width: int = 6) -> np.ndarray:
    return np.arange(height * width, dtype=np.uint16).reshape(height, width) * 100


def test_a_gray_frame_is_stretched_into_opaque_gray() -> None:
    rgba = to_rgba(detector_frame())

    assert rgba.shape == (8, 6, 4)
    assert rgba.dtype == np.uint8
    assert (rgba[..., 3] == 255).all()
    assert (rgba[..., 0] == rgba[..., 1]).all() and (rgba[..., 1] == rgba[..., 2]).all()
    assert rgba[..., 0].min() == 0 and rgba[..., 0].max() == 255


def test_a_flat_frame_is_black_not_nan() -> None:
    rgba = to_rgba(np.full((4, 4), 1000, dtype=np.uint16))

    assert (rgba[..., :3] == 0).all()


def test_an_rgb_frame_gets_an_opaque_alpha_and_rgba_is_taken_as_it_is() -> None:
    rgb = np.random.default_rng(0).integers(0, 255, (4, 5, 3), dtype=np.uint8)
    rgba = to_rgba(rgb)
    assert (rgba[..., :3] == rgb).all() and (rgba[..., 3] == 255).all()
    assert to_rgba(rgba) is rgba


def test_what_is_no_image_is_refused() -> None:
    with pytest.raises(ValueError):
        to_rgba(np.zeros((2, 2, 2, 2)))


def test_a_data_frame_reads_back_as_it_was_sent() -> None:
    values = np.linspace(0, 1, 512, dtype=np.float16)
    packet = frames.encode(7, values)

    assert len(packet) == frames.HEADER.size + 1024
    frame = frames.decode(packet, "float16", (512,))
    assert frame.sequence == 7 and frame.sent_at_us > 0
    assert (frame.values == values).all()


def test_a_data_stream_of_more_than_a_packet_is_refused() -> None:
    with pytest.raises(ValueError, match="2048 bytes"):
        DataStream(
            "spectrum",
            dtype="float32",
            shape=(512,),
            axes=[Axis("wavelength", AxisType.SPECTRUM)],
        )


#: One frame as it is on the wire: sequence 42, sent at 1795000000123456 us, float16 values
#: 1, -2, 0.5 and 1024. Orkestrator's ``lovekit/streams/frame.test.ts`` reads the same bytes.
GOLDEN = "010000002a000000401261018b600600003c00c000380064"


def test_a_frame_is_read_as_every_client_reads_it() -> None:
    frame = frames.decode(bytes.fromhex(GOLDEN), "float16", (4,))

    assert (frame.sequence, frame.sent_at_us) == (42, 1_795_000_000_123_456)
    assert frame.values.tolist() == [1.0, -2.0, 0.5, 1024.0]
    assert frames.encode(42, frame.values)[:8] == bytes.fromhex(GOLDEN)[:8]
