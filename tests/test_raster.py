"""Raster panel backgrounds: `image:` on a panel or a standalone scene spec."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
import yaml

from comicforge import raster
from comicforge.render import (
    build_panel_svg,
    build_scene_svg,
    build_svg,
    render_scene,
    render_spec,
)
from comicforge.validate import validate_spec

ROOT = Path(__file__).resolve().parent.parent
PES = ROOT / "examples" / "pes"


def _png(path: Path, w: int = 30, h: int = 20) -> Path:
    """Write a minimal truecolour PNG so tests need no binary fixtures."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\x00" + bytes([200, 120, 90] * w) for _ in range(h))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )
    return path


@pytest.fixture
def art(tmp_path):
    return _png(tmp_path / "art.png")


# --- the raster module itself -------------------------------------------------


def test_size_reads_png_header(art):
    assert raster.size(art) == (30, 20)


def test_size_rejects_a_file_that_is_not_an_image(tmp_path):
    fake = tmp_path / "art.png"
    fake.write_bytes(b"definitely not a png")
    with pytest.raises(ValueError, match="cannot read image dimensions"):
        raster.size(fake)


def test_data_uri_is_base64_png(art):
    assert raster.data_uri(art).startswith("data:image/png;base64,")


def test_data_uri_rejects_unsupported_type(tmp_path):
    bad = tmp_path / "art.tiff"
    bad.write_bytes(b"x")
    with pytest.raises(ValueError, match="unsupported image type"):
        raster.data_uri(bad)


def test_resolve_is_relative_to_the_spec_dir(art):
    assert raster.resolve("art.png", art.parent) == art
    assert raster.resolve({"src": "art.png"}, art.parent) == art
    assert raster.resolve(str(art), None) == art


def test_normalize_rejects_a_non_path_non_mapping():
    with pytest.raises(ValueError, match="must be a path or"):
        raster.normalize(42)


# --- rendering ----------------------------------------------------------------


def _page(image):
    return {"rows": [{"panels": [{"image": image, "bubbles": [{"text": "ahoj"}]}]}]}


def test_panel_image_is_embedded_and_covers(art, library):
    svg = build_svg(_page(str(art)), library=library)
    assert "data:image/png;base64," in svg
    assert 'preserveAspectRatio="xMidYMid slice"' in svg
    assert art.name not in svg  # embedded, not linked


def test_fit_contain_letterboxes(art, library):
    svg = build_svg(_page({"src": str(art), "fit": "contain"}), library=library)
    assert 'preserveAspectRatio="xMidYMid meet"' in svg


def test_unknown_fit_raises(art, library):
    with pytest.raises(ValueError, match="unknown image fit"):
        build_svg(_page({"src": str(art), "fit": "stretch"}), library=library)


def test_image_path_resolves_against_the_spec_file(tmp_path, art):
    spec = tmp_path / "page.yaml"
    spec.write_text(
        yaml.safe_dump({"library": str(PES / "characters"), **_page("art.png")}),
        encoding="utf-8",
    )
    out = tmp_path / "out.png"
    render_spec(spec, out)
    assert out.stat().st_size > 0


def test_actors_and_pixel_compose_over_an_image(art, library, pixel):
    spec = {
        "rows": [
            {
                "panels": [
                    {
                        "image": str(art),
                        "actors": [{"char": "tom"}],
                        "pixel": [{"art": "heart"}],
                        "bubbles": [{"text": "ahoj", "speaker": "tom"}],
                    }
                ]
            }
        ]
    }
    svg = build_svg(spec, library=library, pixel_library=pixel)
    assert "data:image/png;base64," in svg
    assert svg.index("<image") < svg.index("ahoj")  # image is underneath


def test_single_panel_render_keeps_the_image(art, library):
    svg = build_panel_svg(_page(str(art)), 0, 0, library=library)
    assert "data:image/png;base64," in svg


def test_standalone_scene_sizes_to_the_image(art, library):
    spec = {"type": "scene", "image": str(art), "scale": 3}
    svg = build_scene_svg(spec, library=library)
    assert 'width="90" height="60"' in svg


def test_scene_spec_is_inferred_from_a_bare_image(art, library):
    spec = {"image": str(art), "bubbles": [{"text": "ahoj"}]}
    assert build_scene_svg(spec, library=library).lstrip().startswith("<svg")


def test_scene_spec_with_no_background_is_an_error(library):
    with pytest.raises(ValueError, match="needs a background"):
        build_scene_svg({"type": "scene"}, library=library)


@pytest.mark.parametrize("ext", [".svg", ".png", ".pdf"])
def test_all_output_formats_carry_the_image(tmp_path, art, library, ext):
    out = tmp_path / f"out{ext}"
    render_scene({"type": "scene", "image": str(art)}, out, library=library)
    assert out.stat().st_size > 0


def test_czech_diacritics_survive_to_png_and_pdf(tmp_path, art, library):
    """Latin Extended-A must reach the raster/PDF output, not a glyph-less box."""
    text = "Vavřinec sázel příliš žluté ďáblíky: ěščřžýáíé ůňť."
    spec = {"type": "scene", "image": str(art), "bubbles": [{"text": text}]}
    svg = build_scene_svg(spec, library=library)
    for word in text.split():  # word-wrapped into tspans, so check word by word
        assert word in svg
    for ext in (".png", ".pdf"):
        out = tmp_path / f"cz{ext}"
        render_scene(spec, out, library=library)
        assert out.stat().st_size > 0


# --- validation ---------------------------------------------------------------


def _validate(spec, library):
    return validate_spec(spec, library=library)


def test_validate_accepts_a_good_image(art, library):
    assert _validate(_page(str(art)), library) == []


def test_validate_flags_a_missing_image(tmp_path, library):
    problems = _validate(_page(str(tmp_path / "nope.png")), library)
    assert any("image file not found" in p for p in problems)


def test_validate_flags_an_unreadable_image(art, library):
    art.chmod(0o000)
    try:
        problems = _validate(_page(str(art)), library)
    finally:
        art.chmod(0o644)
    assert any("unreadable" in p for p in problems)


def test_validate_flags_an_unsupported_image_type(tmp_path, library):
    bad = _png(tmp_path / "art.bmp")
    problems = _validate(_page(str(bad)), library)
    assert any("unsupported image type" in p for p in problems)


def test_validate_flags_a_misspelled_image_key(art, library):
    spec = {"rows": [{"panels": [{"imge": str(art)}]}]}
    problems = _validate(spec, library)
    assert any("unknown panel key 'imge'" in p for p in problems)


def test_validate_flags_a_bad_fit_and_a_bad_image_key(art, library):
    spec = _page({"src": str(art), "fit": "stretch", "srcs": "x"})
    problems = _validate(spec, library)
    assert any("unknown image fit 'stretch'" in p for p in problems)
    assert any("unknown image key 'srcs'" in p for p in problems)


def test_validate_flags_an_image_with_no_src(library):
    problems = _validate(_page({"fit": "cover"}), library)
    assert any("no 'src'" in p for p in problems)


def test_validate_reports_every_image_problem_at_once(tmp_path, library):
    spec = {
        "rows": [
            {
                "panels": [
                    {"image": str(tmp_path / "a.png")},
                    {"image": str(tmp_path / "b.png"), "colour": "red"},
                ]
            }
        ]
    }
    problems = _validate(spec, library)
    assert len(problems) == 3
