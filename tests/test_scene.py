import pytest

from comicforge.scene import cover


def test_manifest_lists_seed_scenes(scenes):
    man = scenes.manifest()
    assert {"dvur", "pokoj"} <= set(man)
    assert man["dvur"]["slots"]["weather"] == ["clear", "rain"]


def test_scene_without_slots_loads(scenes):
    pokoj = scenes.get("pokoj")
    assert pokoj.slots == {}
    assert "<rect" in pokoj.compose_inner({})


def test_weather_overlay_changes_output(scenes):
    dvur = scenes.get("dvur")
    clear = dvur.compose_inner({"weather": "clear"})
    rain = dvur.compose_inner({"weather": "rain"})
    assert rain != clear
    assert len(rain) > len(clear)


def test_get_unknown_scene_raises(scenes):
    with pytest.raises(KeyError):
        scenes.get("atlantis")


def test_cover_emits_scaled_group(scenes):
    dvur = scenes.get("dvur")
    svg = cover(dvur, {}, px=0, py=0, pw=640, ph=400)
    assert svg.startswith("<g transform=") and "scale(" in svg
