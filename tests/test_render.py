from pathlib import Path

import pytest

from comicforge.bubbles import bubble_size
from comicforge.render import (
    _layout,
    build_character_svg,
    build_scene_svg,
    build_svg,
    render_character,
    render_scene,
    render_spec,
)

ROOT = Path(__file__).resolve().parent.parent


def test_load_spec_reads_example(example_spec):
    assert "rows" in example_spec
    assert example_spec["rows"]


def test_build_svg_produces_valid_root(example_spec, library, scenes, pixel):
    svg = build_svg(example_spec, library=library, scenes=scenes, pixel_library=pixel)
    assert svg.lstrip().startswith("<svg")
    assert svg.rstrip().endswith("</svg>")


def test_render_spec_writes_png(example_spec, library, scenes, pixel, tmp_path):
    out = tmp_path / "page.png"
    svg = render_spec(
        example_spec, out, library=library, scenes=scenes, pixel_library=pixel
    )
    assert out.exists() and out.stat().st_size > 0
    assert "<svg" in svg


def test_render_spec_loads_spec_from_path(tmp_path, library, scenes, pixel):
    spec_path = ROOT / "examples" / "pes" / "pages" / "slepice.yaml"
    out = tmp_path / "from_path.svg"
    render_spec(spec_path, out, library=library, pixel_library=pixel)
    assert out.read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_render_spec_by_path_resolves_relative_dirs(tmp_path):
    """Spec loaded by path must resolve library:/pixel_dir: relative to the spec
    file's directory — no library or pixel_library overrides passed."""
    spec_path = ROOT / "examples" / "pes" / "pages" / "slepice.yaml"
    out = tmp_path / "slepice_resolved.svg"
    render_spec(spec_path, out)
    svg = out.read_text(encoding="utf-8")
    assert svg.lstrip().startswith("<svg")
    assert svg.rstrip().endswith("</svg>")


def test_render_spec_rejects_unknown_extension(
    example_spec, library, scenes, pixel, tmp_path
):
    with pytest.raises(ValueError):
        render_spec(
            example_spec,
            tmp_path / "page.gif",
            library=library,
            scenes=scenes,
            pixel_library=pixel,
        )


def test_panel_scene_embeds_background(library, scenes):
    spec = {
        "rows": [{"panels": [{"scene": "pokoj", "actors": []}]}],
    }
    svg = build_svg(spec, library=library, scenes=scenes)
    # the scene's window frame colour should appear in the rendered panel
    assert "#7a5230" in svg


def test_bubble_style_central_and_override(library):
    spec = {
        "bubble_style": {"uppercase": True, "font_size": 20},
        "rows": [
            {
                "panels": [
                    {
                        "bubbles": [
                            {"text": "hello there"},
                            {"text": "quiet one", "uppercase": False},
                            {"text": "small", "fs": 12},
                        ]
                    }
                ]
            }
        ],
    }
    svg = build_svg(spec, library=library)
    assert "HELLO THERE" in svg  # central uppercase applied
    assert "quiet one" in svg  # per-bubble opts out of caps
    assert 'font-size="20"' in svg  # central font size applied
    assert 'font-size="12"' in svg  # per-bubble fs overrides central


def test_build_scene_svg_sizes_to_scene(illustration_spec, library, scenes):
    svg = build_scene_svg(illustration_spec, library=library, scenes=scenes)
    assert svg.lstrip().startswith("<svg")
    # dvur viewbox 320x200 at scale 3 -> 960x600
    assert 'width="960"' in svg and 'height="600"' in svg


def test_render_scene_writes_png(illustration_spec, library, scenes, tmp_path):
    out = tmp_path / "scene.png"
    render_scene(illustration_spec, out, library=library, scenes=scenes)
    assert out.exists() and out.stat().st_size > 0


def test_build_character_svg_sizes_to_pose(library):
    # bara 'sit' pose viewbox at scale 1, no padding -> exactly the viewbox
    svg = build_character_svg("bara", {}, "sit", library=library, scale=1.0, pad=0.0)
    sit = library.get("bara").poses["sit"]
    assert f'width="{sit.w:.0f}"' in svg and f'height="{sit.h:.0f}"' in svg


def test_build_character_svg_pose_selects_body(library):
    sit = build_character_svg("bara", {}, "sit", library=library)
    walk = build_character_svg("bara", {}, "walk", library=library)
    assert sit != walk


def test_render_character_writes_png(library, tmp_path):
    out = tmp_path / "bara.png"
    render_character("bara", out, {"face": "happy"}, "sit", library=library)
    assert out.exists() and out.stat().st_size > 0


def test_build_character_svg_white_bg_default(library):
    svg = build_character_svg("tom", {}, library=library)
    assert 'fill="#ffffff"' in svg


def test_build_character_svg_flip(library):
    plain = build_character_svg("tom", {}, library=library)
    flipped = build_character_svg("tom", {}, library=library, flip=True)
    assert plain != flipped


def test_bubble_style_full_look(library):
    spec = {
        "bubble_style": {
            "pad": 6,
            "stroke_width": 1.2,
            "stroke": "#5a4e42",
            "radius": 4,
        },
        "rows": [{"panels": [{"bubbles": [{"text": "hello"}]}]}],
    }
    svg = build_svg(spec, library=library)
    assert 'stroke="#5a4e42" stroke-width="1.20"' in svg
    assert 'rx="4.0"' in svg


def test_bubble_at_anchors_stack_per_column(library):
    spec = {
        "page": [200, 200],
        "px_per_mm": 1,
        "margin_mm": 0,
        "rows": [
            {
                "panels": [
                    {
                        "bubbles": [
                            {"text": "a", "at": "tl"},
                            {"text": "b", "at": "tr"},
                            {"text": "c", "at": "bl"},
                        ]
                    }
                ]
            }
        ],
    }
    svg = build_svg(spec, library=library)
    rects = [
        ln
        for ln in svg.split("<rect")
        if 'fill="#ffffff"' in ln and ln.startswith(" x=")
    ]
    xs = [float(r.split('x="')[1].split('"')[0]) for r in rects]
    ys = [float(r.split('y="')[1].split('"')[0]) for r in rects]
    w, h = bubble_size("a")
    assert xs[0] == pytest.approx(8.0)  # tl hugs the left inset
    assert xs[1] == pytest.approx(200 - 8 - w)  # tr hugs the right
    assert ys[0] == ys[1] == pytest.approx(8.0)  # side by side, same top
    assert ys[2] == pytest.approx(200 - 8 - h)  # bl climbs from the bottom


def test_bubble_at_stacks_only_when_overlapping(library):
    wide = "a" * 30  # too wide for tl and tr to share the top edge
    spec = {
        "page": [300, 200],
        "px_per_mm": 1,
        "margin_mm": 0,
        "rows": [
            {
                "panels": [
                    {
                        "bubbles": [
                            {"text": wide, "at": "tl", "max_chars": 30},
                            {"text": "b", "at": "tr"},
                        ]
                    }
                ]
            }
        ],
    }
    svg = build_svg(spec, library=library)
    rects = [
        ln
        for ln in svg.split("<rect")
        if 'fill="#ffffff"' in ln and ln.startswith(" x=")
    ]
    ys = [float(r.split('y="')[1].split('"')[0]) for r in rects]
    _w, h = bubble_size(wide, max_chars=30)
    assert ys[1] == pytest.approx(8 + h + 10)  # pushed under the wide one


def test_bubble_at_unknown_raises(library):
    spec = {"rows": [{"panels": [{"bubbles": [{"text": "a", "at": "nope"}]}]}]}
    with pytest.raises(ValueError, match="anchor"):
        build_svg(spec, library=library)


def test_frame_style_page_and_panel(library):
    spec = {
        "frame": {"width": 1, "color": "#777777", "radius": 0},
        "rows": [{"panels": [{}, {"frame": {"width": 0}}]}],
    }
    svg = build_svg(spec, library=library)
    assert svg.count('stroke="#777777" stroke-width="1"') == 1  # second panel has none
    assert 'rx="0"' in svg


def test_row_height_mm_is_fixed(library):
    spec = {
        "page": [100, 100],
        "px_per_mm": 2,
        "margin_mm": 0,
        "gutter_mm": 0,
        "rows": [{"height_mm": 30, "panels": [{}]}, {"panels": [{}]}],
    }
    heights = [ph for *_, ph in _layout(spec)]
    assert heights == [60, 140]


def test_page_bg_and_title_style(library):
    spec = {
        "bg": "#fbf8f0",
        "title": "A & B",
        "title_style": {"font_size": 20, "color": "#333333"},
        "rows": [{"panels": [{}]}],
    }
    svg = build_svg(spec, library=library)
    assert 'fill="#fbf8f0"' in svg
    assert 'font-size="20" font-weight="bold" fill="#333333">A &amp; B<' in svg
