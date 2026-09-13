"""Raster panel backgrounds: `image:` on a panel or a standalone scene spec."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
import yaml

from comicforge import caption, raster
from comicforge.render import (
    _layout,
    build_panel_svg,
    build_scene_svg,
    build_svg,
    page_squeeze,
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


# --- crop and at --------------------------------------------------------------


def test_at_pins_the_cover_crop_to_an_edge(art, library):
    svg = build_svg(_page({"src": str(art), "at": "t"}), library=library)
    assert 'preserveAspectRatio="xMidYMin slice"' in svg


def test_unknown_at_raises(art, library):
    with pytest.raises(ValueError, match="unknown image anchor"):
        build_svg(_page({"src": str(art), "at": "top"}), library=library)


def test_crop_views_only_the_kept_region(art, library):
    img = {"src": str(art), "crop": {"top": 2, "bottom": 3, "right": 5}}
    svg = build_svg(_page(img), library=library)
    assert 'viewBox="0 2 25 15"' in svg


def test_crop_draws_the_whole_image_inside_the_viewport(art, library):
    img = {"src": str(art), "crop": {"top": 2}}
    svg = build_svg(_page(img), library=library)
    assert '<image width="30" height="20"' in svg


def test_crop_side_must_be_known(art, library):
    with pytest.raises(ValueError, match="unknown image crop side"):
        build_svg(_page({"src": str(art), "crop": {"up": 2}}), library=library)


def test_crop_must_leave_something(art, library):
    with pytest.raises(ValueError, match="leaves nothing"):
        build_svg(
            _page({"src": str(art), "crop": {"top": 10, "bottom": 10}}), library=library
        )


def test_standalone_scene_sizes_to_the_cropped_image(art, library):
    spec = {"type": "scene", "image": {"src": str(art), "crop": {"left": 10}}}
    svg = build_scene_svg(spec, library=library)
    assert 'width="20" height="20"' in svg


def test_validate_accepts_crop_and_at(art, library):
    img = {"src": str(art), "at": "b", "crop": {"top": 4}}
    assert _validate(_page(img), library) == []


def test_validate_flags_a_bad_at(art, library):
    problems = _validate(_page({"src": str(art), "at": "top"}), library)
    assert any("unknown image anchor" in p for p in problems)


def test_validate_flags_a_negative_crop(art, library):
    problems = _validate(_page({"src": str(art), "crop": {"top": -1}}), library)
    assert any("non-negative pixel count" in p for p in problems)


def test_validate_flags_a_crop_that_eats_the_image(art, library):
    problems = _validate(_page({"src": str(art), "crop": {"left": 30}}), library)
    assert any("leaves nothing" in p for p in problems)


# --- height: auto rows ----------------------------------------------------------


def _auto_page(*rows, **page):
    """A 100x100 mm page at 1 px/mm with no margins or gutters."""
    base = {"page": [100, 100], "px_per_mm": 1, "margin_mm": 0, "gutter_mm": 0}
    return {**base, **page, "rows": list(rows)}


def _heights(spec):
    return [ph for _ri, ci, *_, ph in _layout(spec) if ci == 0]


def test_auto_row_takes_the_image_aspect_at_panel_width(art):
    spec = _auto_page(
        {"height": "auto", "panels": [{"image": str(art)}]}, {"panels": [{}]}
    )
    assert _heights(spec) == [pytest.approx(100 * 20 / 30), pytest.approx(100 / 3)]


def test_auto_row_measures_the_cropped_image(art):
    img = {"src": str(art), "crop": {"top": 5, "bottom": 5}}
    spec = _auto_page({"height": "auto", "panels": [{"image": img}]})
    assert _heights(spec) == [pytest.approx(100 * 10 / 30)]


def test_auto_row_adds_the_caption_band(art):
    cap = {"text": "Rain came."}
    spec = _auto_page(
        {"height": "auto", "panels": [{"image": str(art), "caption": cap}]}
    )
    assert _heights(spec) == [pytest.approx(100 * 20 / 30 + caption.height(cap))]


def test_auto_rows_that_overflow_squeeze_their_art_but_not_captions(art):
    cap = {"text": "Rain came."}
    row = {"height": "auto", "panels": [{"image": str(art), "caption": cap}]}
    # 2 x (66.7 art + band) > 100: the art shrinks until each row is half
    assert _heights(_auto_page(row, row)) == [pytest.approx(50), pytest.approx(50)]


def test_squeezed_auto_rows_keep_their_caption_bands_whole(art):
    cap = {"text": "Rain came."}
    band = caption.height(cap)
    with_cap = {"height": "auto", "panels": [{"image": str(art), "caption": cap}]}
    bare = {"height": "auto", "panels": [{"image": str(art)}]}
    art_h = (100 - band) / 2  # both arts squeezed alike, the band on top of one
    assert _heights(_auto_page(with_cap, bare)) == [
        pytest.approx(art_h + band),
        pytest.approx(art_h),
    ]


def test_auto_row_is_as_tall_as_its_tallest_panel(art, tmp_path):
    tall = _png(tmp_path / "tall.png", w=10, h=20)
    spec = _auto_page(
        {"height": "auto", "panels": [{"image": str(art)}, {"image": str(tall)}]}
    )
    assert _heights(spec) == [pytest.approx(100)]  # the 50 px wide, 1:2 image


def test_auto_row_without_an_image_raises():
    with pytest.raises(ValueError, match="needs a panel with an `image:`"):
        _heights(_auto_page({"height": "auto", "panels": [{}]}))


def test_auto_row_images_resolve_against_the_spec_dir(art):
    spec = _auto_page({"height": "auto", "panels": [{"image": art.name}]})
    heights = [ph for *_, ph in _layout(spec, art.parent)]
    assert heights == [pytest.approx(100 * 20 / 30)]


def test_validate_flags_an_auto_row_without_an_image(library):
    problems = _validate({"rows": [{"height": "auto", "panels": [{}]}]}, library)
    assert any("needs a panel with an `image:`" in p for p in problems)


def test_validate_flags_a_bad_row_height(library):
    problems = _validate({"rows": [{"height": "tall", "panels": [{}]}]}, library)
    assert any("row height must be" in p for p in problems)


def test_page_squeeze_is_one_when_auto_rows_fit(art):
    spec = _auto_page({"height": "auto", "panels": [{"image": str(art)}]})
    assert page_squeeze(spec) == 1.0


def test_page_squeeze_reports_the_art_scale_of_an_overflowing_page(art):
    row = {"height": "auto", "panels": [{"image": str(art)}]}
    # two 66.7 px arts in 100 px: each scaled to 50
    assert page_squeeze(_auto_page(row, row)) == pytest.approx(0.75)


def test_page_squeeze_reads_a_spec_file_relative_to_it(art):
    spec = art.parent / "page.yaml"
    row = {"height": "auto", "panels": [{"image": art.name}]}
    spec.write_text(yaml.safe_dump(_auto_page(row, row)), encoding="utf-8")
    assert page_squeeze(spec) == pytest.approx(0.75)
