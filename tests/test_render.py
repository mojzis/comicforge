from pathlib import Path

import pytest

from comicforge.render import (
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
