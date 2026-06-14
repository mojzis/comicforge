from pathlib import Path

import pytest

from comicforge.inspire import (
    Item,
    Theme,
    build_prompt,
    generate,
    load_items,
    load_theme,
)

ROOT = Path(__file__).resolve().parent.parent
PES = ROOT / "examples" / "pes"


def test_load_theme_reads_palette_and_style():
    theme = load_theme(PES / "theme.yaml")
    assert theme.style
    assert "#f4d35e" in theme.palette
    assert theme.aspect_ratio == "1:1"


def test_load_theme_missing_file_returns_defaults(tmp_path):
    theme = load_theme(tmp_path / "nope.yaml")
    assert theme == Theme()


def test_load_items_accepts_items_key_and_aliases(tmp_path):
    spec = tmp_path / "refs.yaml"
    spec.write_text(
        "items:\n  - {id: a, prompt: foo}\n  - {name: b, description: bar}\n",
        encoding="utf-8",
    )
    items = load_items(spec)
    assert [(i.id, i.prompt) for i in items] == [("a", "foo"), ("b", "bar")]


def test_load_items_bare_list(tmp_path):
    spec = tmp_path / "refs.yaml"
    spec.write_text("- {id: x, prompt: y}\n", encoding="utf-8")
    assert load_items(spec)[0].id == "x"


def test_load_items_rejects_incomplete_entry(tmp_path):
    spec = tmp_path / "refs.yaml"
    spec.write_text("- {id: x}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="needs both an id and a prompt"):
        load_items(spec)


def test_build_prompt_blends_theme_and_subject():
    theme = Theme(style="STYLE.", palette=["#fff"], mood="calm", negative="NO TEXT.")
    prompt = build_prompt(theme, Item(id="t", prompt="a cat"))
    assert "STYLE." in prompt
    assert "Subject: a cat" in prompt
    assert "#fff" in prompt
    assert "Mood: calm." in prompt
    assert "NO TEXT." in prompt


def test_dry_run_writes_prompts_only(tmp_path):
    (tmp_path / "theme.yaml").write_text("style: S\n", encoding="utf-8")
    spec = tmp_path / "references.yaml"
    spec.write_text(
        "items:\n  - {id: tom, prompt: a boy}\n  - {id: dog, prompt: a dog}\n",
        encoding="utf-8",
    )
    written = generate(spec, dry_run=True)
    out = tmp_path / "references"
    assert (out / "tom.prompt.txt").exists()
    assert (out / "dog.prompt.txt").exists()
    assert not list(out.glob("*.png"))
    assert "Subject: a boy" in (out / "tom.prompt.txt").read_text()
    assert set(written) == {out / "tom.prompt.txt", out / "dog.prompt.txt"}


def test_dry_run_only_filter(tmp_path):
    spec = tmp_path / "references.yaml"
    spec.write_text(
        "items:\n  - {id: tom, prompt: a}\n  - {id: dog, prompt: b}\n",
        encoding="utf-8",
    )
    generate(spec, only={"tom"}, dry_run=True)
    out = tmp_path / "references"
    assert (out / "tom.prompt.txt").exists()
    assert not (out / "dog.prompt.txt").exists()


def test_example_references_spec_loads():
    items = load_items(PES / "references.yaml")
    assert {i.id for i in items} == {"tom", "bara", "dvur"}
