import pytest


def test_manifest_lists_seed_characters(library):
    man = library.manifest()
    assert {"tom", "bara"} <= set(man)
    assert "slots" in man["tom"]


def test_get_caches_character(library):
    first = library.get("tom")
    assert library.get("tom") is first


def test_get_unknown_character_raises(library):
    with pytest.raises(KeyError):
        library.get("nobody")


def test_place_emits_group(library):
    tom = library.get("tom")
    svg = tom.place({"face": "happy"}, cx=100, cy=100, height=200)
    assert "<g" in svg and "</g>" in svg
