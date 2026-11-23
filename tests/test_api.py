from lovekit.lovekit import Lovekit


def test_importability() -> None:
    """Test that the Lovekit module can be imported without errors."""
    assert Lovekit is not None
