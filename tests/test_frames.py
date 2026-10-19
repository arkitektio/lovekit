"""What a video track takes: RGBA uint8 frames, made from what cameras and detectors give."""

import numpy as np
import pytest

from lovekit import to_rgba


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
