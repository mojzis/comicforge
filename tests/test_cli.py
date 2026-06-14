from pathlib import Path

import pytest

from comicforge.cli import _default_out, _parse_selection, main

ROOT = Path(__file__).resolve().parent.parent
PES = ROOT / "examples" / "pes"


def test_parse_selection_bare_pose_and_variant(library):
    char = library.get("bara")
    selection, pose = _parse_selection(char, ["sit", "happy"], None)
    assert pose == "sit"
    assert selection == {"face": "happy"}


def test_parse_selection_key_value(library):
    char = library.get("bara")
    selection, pose = _parse_selection(char, ["pose=walk", "face=neutral"], None)
    assert pose == "walk"
    assert selection == {"face": "neutral"}


def test_parse_selection_unknown_token_exits(library):
    char = library.get("bara")
    with pytest.raises(SystemExit):
        _parse_selection(char, ["bogus"], None)


def test_character_command_writes_full_and_thumb(tmp_path):
    out = tmp_path / "bara.png"
    main(
        [
            "character",
            "bara",
            "sit",
            "happy",
            "--library",
            str(PES / "characters"),
            "-o",
            str(out),
        ]
    )
    thumb = tmp_path / "bara.small.png"
    assert out.exists() and out.stat().st_size > 0
    assert thumb.exists() and thumb.stat().st_size > 0
    # the companion is smaller on disk than the full render
    assert thumb.stat().st_size < out.stat().st_size


def test_default_out_is_timestamped_under_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = _default_out("bara")
    assert out.parent == Path("output")
    assert out.name.startswith("bara-") and out.suffix == ".png"
    assert (tmp_path / "output").is_dir()


def test_character_command_defaults_into_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["character", "bara", "sit", "--library", str(PES / "characters")])
    pngs = sorted((tmp_path / "output").glob("bara-*.png"))
    # full + .small companion
    assert any(p.name.endswith(".small.png") for p in pngs)
    assert any(not p.name.endswith(".small.png") for p in pngs)


def test_character_command_thumb_px_zero_skips_thumb(tmp_path):
    out = tmp_path / "tom.png"
    main(
        [
            "character",
            "tom",
            "--library",
            str(PES / "characters"),
            "-o",
            str(out),
            "--thumb-px",
            "0",
        ]
    )
    assert out.exists()
    assert not (tmp_path / "tom.small.png").exists()
