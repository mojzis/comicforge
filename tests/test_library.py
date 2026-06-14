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


def test_flat_character_is_single_pose(library):
    tom = library.get("tom")
    assert list(tom.poses) == ["default"]
    # flat characters are not advertised as multi-pose in the manifest
    assert "poses" not in library.manifest()["tom"]


def test_posed_character_lists_poses(library):
    bara = library.get("bara")
    assert set(bara.poses) == {"sit", "walk"}
    assert bara.default_pose == "sit"
    man = library.manifest()["bara"]
    assert set(man["poses"]) == {"sit", "walk"}
    assert man["default_pose"] == "sit"


def test_unknown_pose_raises(library):
    with pytest.raises(ValueError):
        library.get("bara").place({"face": "happy"}, 0, 0, 100, pose="fly")


def test_shared_face_reanchors_per_pose(library):
    """The same face overlay is translated onto the walk pose (anchor differs)."""
    bara = library.get("bara")
    sit = bara.compose_inner({"face": "happy"}, pose="sit")
    walk = bara.compose_inner({"face": "happy"}, pose="walk")
    # sit's anchor equals the canonical anchor -> no shift; walk's differs -> shift
    assert "translate(12.00,-8.00)" in walk
    assert "translate(12.00,-8.00)" not in sit
