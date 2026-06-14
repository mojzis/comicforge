import pytest

from comicforge import pixelart


def test_dims_uses_widest_row():
    assert pixelart.dims(["x", "xxx", "xx"]) == (3, 3)


def test_sprite_skips_blanks():
    svg = pixelart.sprite_svg(["a.", ".a"], {"a": "#ff0000"})
    assert svg.count("<rect") == 2
    assert "#ff0000" in svg


def test_resolve_builtin(pixel):
    inner, cols, rows = pixelart.resolve({"art": "heart"}, pixel)
    assert "<rect" in inner
    assert cols > 0 and rows > 0


def test_resolve_unknown_builtin_raises(pixel):
    with pytest.raises(KeyError):
        pixelart.resolve({"art": "no-such-art"}, pixel)


def test_resolve_no_library_raises():
    with pytest.raises(ValueError, match="pixel library"):
        pixelart.resolve({"art": "heart"})


def test_resolve_custom_grid():
    inner, cols, rows = pixelart.resolve(
        {"grid": ["ab", "ba"], "palette": {"a": "#000", "b": "#fff"}}
    )
    assert (cols, rows) == (2, 2)
    assert inner.count("<rect") == 4


def test_pixel_library_get(pixel):
    data = pixel.get("heart")
    assert "grid" in data and "palette" in data


def test_pixel_library_missing_raises(pixel):
    with pytest.raises(KeyError, match="no-such-art"):
        pixel.get("no-such-art")
