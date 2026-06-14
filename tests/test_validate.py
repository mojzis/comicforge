from pathlib import Path

import pytest

from comicforge.cli import main
from comicforge.library import Library
from comicforge.pixelart import PixelLibrary
from comicforge.render import build_scene_svg, build_svg
from comicforge.scene import SceneLibrary
from comicforge.validate import validate_spec

ROOT = Path(__file__).resolve().parent.parent
PES = ROOT / "examples" / "pes"


def _libargs():
    return {
        "library": Library(PES / "characters"),
        "scenes": SceneLibrary(PES / "scenes"),
        "pixel_library": PixelLibrary(PES / "pixel"),
    }


def test_demo_specs_validate_clean():
    for name in ("slepice", "kosticka"):
        assert validate_spec(PES / "pages" / f"{name}.yaml", **_libargs()) == []


def test_scene_spec_validates_clean():
    assert validate_spec(PES / "pages" / "dvur-scene.yaml", **_libargs()) == []


def test_catches_missing_character_and_bad_variant():
    spec = {
        "rows": [
            {
                "panels": [
                    {
                        "actors": [
                            {"char": "ghost"},
                            {"char": "tom", "face": "nope"},
                        ]
                    }
                ]
            }
        ]
    }
    problems = validate_spec(spec, **_libargs())
    assert any("ghost" in p for p in problems)
    assert any("nope" in p and "face" in p for p in problems)


def test_catches_typo_slot_key():
    # render silently ignores 'fcae'; validate must flag it
    spec = {"rows": [{"panels": [{"actors": [{"char": "tom", "fcae": "happy"}]}]}]}
    problems = validate_spec(spec, **_libargs())
    assert any("fcae" in p for p in problems)


def test_catches_bad_pose_and_unknown_bubble():
    spec = {
        "rows": [
            {
                "panels": [
                    {
                        "actors": [{"char": "bara", "pose": "fly"}],
                        "bubbles": [
                            {"text": "hi", "kind": "yell", "speaker": "nobody"}
                        ],
                    }
                ]
            }
        ]
    }
    problems = validate_spec(spec, **_libargs())
    assert any("pose 'fly'" in p for p in problems)
    assert any("kind 'yell'" in p for p in problems)
    assert any("speaker 'nobody'" in p for p in problems)


def test_missing_rows_reported():
    assert validate_spec({}, **_libargs()) == ["page spec has no 'rows'"]


def test_scene_typed_spec_must_not_have_rows():
    spec = {"type": "scene", "scene": "dvur", "rows": []}
    problems = validate_spec(spec, **_libargs())
    assert any("must not have 'rows'" in p for p in problems)


def test_unknown_spec_type_reported():
    assert validate_spec({"type": "panel"}, **_libargs()) == [
        "unknown spec type 'panel'; use one of ['page', 'scene']"
    ]


def test_render_rejects_scene_spec():
    with pytest.raises(ValueError, match="comicforge scene"):
        build_svg({"type": "scene", "scene": "dvur"})
    with pytest.raises(ValueError, match="comicforge render"):
        build_scene_svg({"type": "page", "rows": []})


def test_cli_returns_zero_on_clean_spec():
    rc = main(
        [
            "validate",
            str(PES / "pages" / "slepice.yaml"),
            "--library",
            str(PES / "characters"),
            "--pixel-dir",
            str(PES / "pixel"),
        ]
    )
    assert rc == 0


def test_cli_returns_one_on_broken_spec(tmp_path):
    spec = tmp_path / "broken.yaml"
    spec.write_text(
        f"library: {PES / 'characters'}\n"
        "rows:\n  - panels:\n      - actors:\n          - {char: ghost}\n"
    )
    rc = main(["validate", str(spec)])
    assert rc == 1
