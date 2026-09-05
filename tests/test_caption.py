import pytest

from comicforge import caption
from comicforge.render import build_svg


def test_height_zero_without_caption():
    assert caption.height(None) == 0


def test_height_grows_with_lines():
    one = caption.height("short")
    two = caption.height({"text": "one two three four", "max_chars": 8})
    assert two > one
    assert one == pytest.approx(13 * 1.25 + 16)


def test_normalize_rejects_empty():
    with pytest.raises(ValueError):
        caption.normalize({"max_chars": 10})


def test_band_shrinks_art_and_keeps_frame(library):
    spec = {
        "page": [100, 100],
        "px_per_mm": 1,
        "margin_mm": 0,
        "rows": [
            {
                "panels": [
                    {"caption": "Rain came.", "bubbles": [{"text": "hi", "at": "bl"}]}
                ]
            }
        ],
    }
    svg = build_svg(spec, library=library)
    assert "Rain came." in svg
    band = caption.height("Rain came.")
    # bubble climbs from the bottom of the *art*, above the band
    rects = [
        ln
        for ln in svg.split("<rect")
        if 'fill="#ffffff"' in ln and ln.startswith(" x=")
    ]
    y = float(rects[-1].split('y="')[1].split('"')[0])
    h = float(rects[-1].split('height="')[1].split('"')[0])
    assert y + h == pytest.approx(100 - band - 8, abs=0.1)
    # frame still spans the whole box
    assert 'height="100.0" rx="10" fill="none"' in svg


def test_caption_style_and_align(library):
    spec = {
        "caption_style": {"font_size": 20, "align": "center", "bg": "#eeeeee"},
        "rows": [{"panels": [{"caption": "x"}]}],
    }
    svg = build_svg(spec, library=library)
    assert 'text-anchor="middle" font-family' in svg
    assert 'fill="#eeeeee"' in svg
    assert 'font-size="20"' in svg
