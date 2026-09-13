import pytest

from comicforge import caption
from comicforge.bubbles import text_width
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


def test_caption_uppercase(library):
    spec = {
        "caption_style": {"uppercase": True},
        "rows": [{"panels": [{"caption": "Rain came."}]}],
    }
    assert "RAIN CAME." in build_svg(spec, library=library)


LONG = "Rain came. Snow came. The goatherd checked every single day, just to be sure."


def test_auto_wrap_uses_more_lines_in_a_narrower_band():
    cap = {"text": LONG, "max_chars": "auto"}
    assert caption.height(cap, width=150) > caption.height(cap, width=600)


def test_auto_wrap_keeps_every_line_inside_the_band():
    st = caption.resolve_style({"max_chars": "auto"})
    widest = max(text_width(ln, 13) for ln in caption.lines({"text": LONG}, st, 200))
    assert widest <= 200 - 2 * st["pad"]


def test_auto_wrap_narrow_em_fits_more_per_line():
    cap = {"text": LONG, "max_chars": "auto"}
    narrow = caption.height(cap, {"em": 0.6}, width=250)
    assert narrow < caption.height(cap, width=250)


def test_auto_wrap_needs_a_width():
    with pytest.raises(ValueError, match="needs the band width"):
        caption.height({"text": LONG, "max_chars": "auto"})


def test_auto_caption_renders_in_a_panel(library):
    spec = {
        "caption_style": {"max_chars": "auto"},
        "rows": [{"panels": [{"caption": LONG}]}],
    }
    assert "goatherd" in build_svg(spec, library=library)
