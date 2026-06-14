"""Statically check a page / scene spec against the libraries it points at.

``render`` only fails on the *first* genuinely unusable thing (a missing
character, a bad variant) and **silently ignores** keys it doesn't recognise —
so a typo like ``fcae: happy`` or ``post: walk`` renders a default-faced,
default-posed actor with no error at all.  ``validate`` walks the whole spec
without drawing anything, collecting *every* problem at once:

- characters / scenes / pixel sprites that don't exist in the library
- poses an actor asks for that the character doesn't have
- slot variants that don't exist for the chosen character+pose / scene
- actor / scene keys that aren't reserved and aren't a real slot (likely typos)
- bubble ``speaker`` that names no actor in the panel, unknown bubble ``kind``
- structural holes (no ``rows``, a row without ``panels``, a bubble with no text)

It returns a list of human-readable problem strings (empty == the spec is sound).
"""

from __future__ import annotations

from pathlib import Path

from .library import Library
from .pixelart import PixelLibrary
from .render import _as_list, _build_libs, load_spec, spec_type
from .scene import SceneLibrary

# keys on an actor / scene dict that are positioning or identity, not slots
_ACTOR_RESERVED = {"char", "pose", "x", "y", "scale", "flip"}
_SCENE_RESERVED = {"name"}
_BUBBLE_KINDS = {"speech", "thought", "shout"}


def _check_actor(actor: dict, lib: Library, where: str, problems: list[str]) -> None:
    name = actor.get("char")
    if not name:
        problems.append(f"{where}: actor with no 'char'")
        return
    try:
        char = lib.get(name)
    except KeyError as e:
        problems.append(f"{where}: {e}")
        return

    pose = actor.get("pose")
    if pose is not None and pose not in char.poses:
        problems.append(
            f"{where}: {name} has no pose '{pose}'. Have: {list(char.poses)}"
        )
        pose = None  # fall back so slot checks still run against a real pose

    slots = char.slots_for(pose)
    for key, value in actor.items():
        if key in _ACTOR_RESERVED:
            continue
        if key not in slots:
            problems.append(
                f"{where}: {name} has no slot '{key}' "
                f"(ignored when rendering). Slots: {sorted(slots)}"
            )
        elif value not in slots[key]:
            problems.append(
                f"{where}: {name} slot '{key}' has no variant '{value}'. "
                f"Have: {slots[key]}"
            )


def _check_scene(sc, scenes, where: str, problems: list[str]) -> None:
    sc = {"name": sc} if isinstance(sc, str) else sc
    name = sc.get("name")
    if not name:
        problems.append(f"{where}: scene with no 'name'")
        return
    try:
        scene = scenes.get(name)
    except KeyError as e:
        problems.append(f"{where}: {e}")
        return
    for key, value in sc.items():
        if key in _SCENE_RESERVED:
            continue
        if key not in scene.slots:
            problems.append(
                f"{where}: scene '{name}' has no slot '{key}' "
                f"(ignored when rendering). Slots: {sorted(scene.slots)}"
            )
        elif value not in scene.slots[key]:
            problems.append(
                f"{where}: scene '{name}' slot '{key}' has no variant '{value}'. "
                f"Have: {scene.slots[key]}"
            )


def _check_pixel(spec, pxlib, where: str, problems: list[str]) -> None:
    if "art" in spec:
        if pxlib is None:
            problems.append(
                f"{where}: pixel art '{spec['art']}' needs a pixel library "
                "(set 'pixel_dir:' in the spec or pass --pixel-dir)"
            )
            return
        try:
            pxlib.get(spec["art"])
        except KeyError as e:
            problems.append(f"{where}: {e}")
    elif "grid" not in spec:
        problems.append(f"{where}: pixel entry has neither 'art' nor 'grid'")


def _check_bubbles(panel: dict, where: str, problems: list[str]) -> None:
    speakers = {a.get("char") for a in panel.get("actors", [])}
    for b in panel.get("bubbles", []):
        if not b.get("text"):
            problems.append(f"{where}: bubble with no 'text'")
        kind = b.get("kind", "speech")
        if kind not in _BUBBLE_KINDS:
            problems.append(
                f"{where}: bubble kind '{kind}' unknown. Have: {sorted(_BUBBLE_KINDS)}"
            )
        speaker = b.get("speaker")
        if speaker is not None and speaker not in speakers:
            problems.append(
                f"{where}: bubble speaker '{speaker}' is not an actor here. "
                f"Actors: {sorted(s for s in speakers if s)}"
            )


def _check_panel(panel, libs, where, problems) -> None:
    lib, scenes, pxlib = libs
    if panel.get("scene") is not None:
        _check_scene(panel["scene"], scenes, where, problems)
    for spec in _as_list(panel.get("pixel")):
        _check_pixel(spec, pxlib, where, problems)
    for actor in panel.get("actors", []):
        _check_actor(actor, lib, where, problems)
    _check_bubbles(panel, where, problems)


def validate_spec(
    spec,
    library: Library | None = None,
    scenes: SceneLibrary | None = None,
    pixel_library: PixelLibrary | None = None,
) -> list[str]:
    """Return every problem found in *spec* (path or dict). Empty == sound.

    A page spec has ``rows`` of ``panels``; a standalone scene spec has a
    top-level ``scene`` and acts as a single panel. Both are validated.
    """
    spec_dir = None
    if not isinstance(spec, dict):
        spec_path = Path(spec)
        spec_dir = spec_path.parent.resolve()
        spec = load_spec(spec_path)

    problems: list[str] = []
    try:
        libs = _build_libs(spec, spec_dir, library, scenes, pixel_library)
    except ValueError as e:
        # a missing library dir is itself the headline problem; nothing else to check
        return [str(e)]

    try:
        kind = spec_type(spec)
    except ValueError as e:
        return [str(e)]

    if kind == "scene":  # standalone illustration, rendered with `scene`
        if "scene" not in spec:
            problems.append("scene spec has no top-level 'scene'")
        if "rows" in spec:
            problems.append(
                "scene spec must not have 'rows' (use a 'page' spec for a grid)"
            )
        _check_panel(spec, libs, "scene", problems)
        return problems

    rows = spec.get("rows")
    if not rows:
        problems.append(
            "page spec has no 'rows'"
            + (" (did you mean type: scene?)" if "scene" in spec else "")
        )
        return problems
    for ri, row in enumerate(rows):
        panels = row.get("panels")
        if not panels:
            problems.append(f"r{ri}: row has no 'panels'")
            continue
        for ci, panel in enumerate(panels):
            _check_panel(panel, libs, f"r{ri}c{ci}", problems)
    return problems
