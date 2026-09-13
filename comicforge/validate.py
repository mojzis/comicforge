"""Statically check a page / scene spec against the libraries it points at.

``render`` only fails on the *first* genuinely unusable thing (a missing
character, a bad variant) and **silently ignores** keys it doesn't recognise —
so a typo like ``fcae: happy`` or ``post: walk`` renders a default-faced,
default-posed actor with no error at all.  ``validate`` walks the whole spec
without drawing anything, collecting *every* problem at once:

- characters / scenes / pixel sprites that don't exist in the library
- raster ``image:`` files that are missing, unreadable, or an unsupported type;
  a bad ``fit`` / ``at`` / ``crop`` (or a crop that leaves nothing)
- a row ``height`` that is neither a weight nor ``auto``, and an ``auto`` row
  with no image to measure
- poses an actor asks for that the character doesn't have
- slot variants that don't exist for the chosen character+pose / scene
- actor / scene keys that aren't reserved and aren't a real slot (likely typos)
- panel keys the renderer doesn't know (``imge:`` for ``image:``, say)
- bubble ``speaker`` that names neither an actor nor a ``speakers:`` point in
  the panel, a malformed ``speakers:`` point, unknown bubble ``kind``, ``at``
  anchor, ``tail``, ``tail_bend`` or ``tail_from``
- structural holes (no ``rows``, a row without ``panels``, a bubble with no text)

It returns a list of human-readable problem strings (empty == the spec is sound).

:func:`check_spec` also lays out every panel's bubbles and returns *warnings*:
things that render fine but read badly — a bubble out of reading order, tails
that cross, a bubble covering a speaker point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import bubbles, caption, layout, raster
from .bubbles import ANCHORS
from .library import Library
from .pixelart import PixelLibrary
from .render import _art_boxes, _as_list, _build_libs, load_spec, spec_type
from .scene import SceneLibrary

# keys on an actor / scene dict that are positioning or identity, not slots
_ACTOR_RESERVED = {"char", "pose", "x", "y", "scale", "flip"}
_SCENE_RESERVED = {"name"}
_BUBBLE_KINDS = {"speech", "thought", "shout"}
# every key `_render_panel` reads off a panel; anything else is a typo
_PANEL_KEYS = {
    "width",
    "bg",
    "frame",
    "caption",
    "scene",
    "image",
    "actors",
    "pixel",
    "bubbles",
    "speakers",
}
_IMAGE_KEYS = {"src", "fit", "at", "crop"}


def _check_keys(keys, known: set[str], label: str, where: str, problems) -> None:
    """Flag keys the renderer silently ignores — almost always a typo."""
    problems.extend(
        f"{where}: unknown {label} key '{key}' "
        f"(ignored when rendering). Known: {sorted(known)}"
        for key in keys
        if key not in known
    )


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


def _check_image(value, spec_dir, where: str, problems: list[str]) -> None:
    try:
        img = raster.normalize(value)
    except ValueError as e:
        problems.append(f"{where}: {e}")
        return
    _check_keys(img, _IMAGE_KEYS, "image", where, problems)
    fit = img.get("fit", "cover")
    if fit not in raster.FITS:
        problems.append(
            f"{where}: unknown image fit '{fit}'. Use one of {sorted(raster.FITS)}"
        )
    for check in (
        lambda: raster.align(img.get("at")),
        lambda: raster.crop_margins(img),
    ):
        try:
            check()
        except ValueError as e:
            problems.append(f"{where}: {e}")
    try:
        path = raster.resolve(value, spec_dir)
    except ValueError as e:
        problems.append(f"{where}: {e}")
        return
    if not path.is_file():
        problems.append(f"{where}: image file not found: {path}")
        return
    if path.suffix.lower() not in raster.MIME:
        problems.append(
            f"{where}: unsupported image type '{path.suffix}' for {path}. "
            f"Supported: {sorted(raster.MIME)}"
        )
    try:
        with path.open("rb") as fh:
            fh.read(1)
    except OSError as e:
        problems.append(f"{where}: image file is unreadable: {path} ({e.strerror})")
        return
    if img.get("crop"):
        try:
            raster.region(img, spec_dir)
        except ValueError as e:
            problems.append(f"{where}: {e}")


def _check_row_height(row: dict, where: str, problems: list[str]) -> None:
    height = row.get("height", 1)
    if height == "auto":
        if "height_mm" not in row and not any(
            p.get("image") is not None for p in row.get("panels") or []
        ):
            problems.append(
                f"{where}: a `height: auto` row needs a panel with an `image:` "
                "to take its height from"
            )
    elif isinstance(height, bool) or not isinstance(height, int | float) or height < 0:
        problems.append(
            f"{where}: row height must be a non-negative weight or 'auto', "
            f"got {height!r}"
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


def _check_speakers(panel: dict, where: str, problems: list[str]) -> set[str]:
    """Flag malformed ``speakers:`` points; return the names given."""
    speakers = panel.get("speakers")
    if speakers is None:
        return set()
    if not isinstance(speakers, dict):
        problems.append(
            f"{where}: speakers must map a name to [x, y], got {speakers!r}"
        )
        return set()
    for name, xy in speakers.items():
        ok = (
            isinstance(xy, list | tuple)
            and len(xy) == len("xy")
            and all(isinstance(v, int | float) and not isinstance(v, bool) for v in xy)
        )
        if not ok:
            problems.append(
                f"{where}: speaker '{name}' needs a point [x, y] in panel "
                f"fractions, got {xy!r}"
            )
    return {str(name) for name in speakers}


def _check_bubbles(panel: dict, where: str, problems: list[str]) -> None:
    actors = {a.get("char") for a in panel.get("actors", [])} - {None}
    speakers = actors | _check_speakers(panel, where, problems)
    for b in panel.get("bubbles", []):
        if not b.get("text"):
            problems.append(f"{where}: bubble with no 'text'")
        kind = b.get("kind", "speech")
        if kind not in _BUBBLE_KINDS:
            problems.append(
                f"{where}: bubble kind '{kind}' unknown. Have: {sorted(_BUBBLE_KINDS)}"
            )
        at = b.get("at")
        if at is not None and at not in ANCHORS:
            problems.append(
                f"{where}: bubble anchor '{at}' unknown. Have: {sorted(ANCHORS)}"
            )
        _check_tail_keys(b, where, problems)
        speaker = b.get("speaker")
        if speaker is not None and speaker not in speakers:
            problems.append(
                f"{where}: bubble speaker '{speaker}' is neither an actor nor a "
                f"`speakers:` point here. Have: {sorted(speakers)}"
            )


def _check_tail_keys(style: dict, where: str, problems: list[str]) -> None:
    """``tail`` / ``tail_bend`` / ``tail_from`` on a bubble or the page's
    ``bubble_style``."""
    shape = style.get("tail")
    if shape is not None and shape not in bubbles.TAIL_SHAPES:
        problems.append(
            f"{where}: tail '{shape}' unknown. Have: {list(bubbles.TAIL_SHAPES)}"
        )
    try:
        bubbles.tail_look({"tail_bend": style.get("tail_bend")})
    except ValueError as e:
        problems.append(f"{where}: {e}")
    try:
        bubbles.tail_from(style.get("tail_from"))
    except ValueError as e:
        problems.append(f"{where}: {e}")


def _layout_warnings(spec, spec_dir, scenes) -> list[str]:
    """Bubble layout warnings for every panel; nothing for a spec too broken
    to lay out (its problems are reported already)."""
    out = []
    try:
        for where, panel, w, h in _art_boxes(spec, spec_dir, scenes):
            placements = layout.layout_bubbles(
                panel, 0, 0, w, h, spec.get("bubble_style")
            )
            points = {
                name: (x * w, y * h)
                for name, (x, y) in layout.speaker_points(panel).items()
            }
            out.extend(
                f"{where}: {msg}" for msg in layout.layout_warnings(placements, points)
            )
    except (ValueError, KeyError, TypeError, IndexError, OSError):
        return out
    return out


def _check_panel(panel, libs, where, problems, spec_dir=None) -> None:
    lib, scenes, pxlib = libs
    try:
        caption.normalize(panel.get("caption"))
    except ValueError as e:
        problems.append(f"{where}: {e}")
    if panel.get("scene") is not None:
        _check_scene(panel["scene"], scenes, where, problems)
    if panel.get("image") is not None:
        _check_image(panel["image"], spec_dir, where, problems)
    for spec in _as_list(panel.get("pixel")):
        _check_pixel(spec, pxlib, where, problems)
    for actor in panel.get("actors", []):
        _check_actor(actor, lib, where, problems)
    _check_bubbles(panel, where, problems)


@dataclass
class Report:
    """What :func:`check_spec` found: *problems* break or silently change the
    render; *warnings* render fine but read badly."""

    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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
    return check_spec(spec, library, scenes, pixel_library).problems


def check_spec(
    spec,
    library: Library | None = None,
    scenes: SceneLibrary | None = None,
    pixel_library: PixelLibrary | None = None,
) -> Report:
    """Every problem in *spec* (path or dict), plus bubble layout warnings."""
    spec_dir = None
    if not isinstance(spec, dict):
        spec_path = Path(spec)
        spec_dir = spec_path.parent.resolve()
        spec = load_spec(spec_path)

    report = Report(problems=_problems(spec, spec_dir, library, scenes, pixel_library))
    if not report.problems:
        _lib, scn, _px = _build_libs(spec, spec_dir, library, scenes, pixel_library)
        report.warnings = _layout_warnings(spec, spec_dir, scn)
    return report


def _problems(spec, spec_dir, library, scenes, pixel_library) -> list[str]:
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
        if "scene" not in spec and "image" not in spec:
            problems.append(
                "scene spec has no background: set a top-level 'scene:' or 'image:'"
            )
        if "rows" in spec:
            problems.append(
                "scene spec must not have 'rows' (use a 'page' spec for a grid)"
            )
        _check_tail_keys(spec.get("bubble_style") or {}, "bubble_style", problems)
        _check_panel(spec, libs, "scene", problems, spec_dir)
        return problems

    rows = spec.get("rows")
    if not rows:
        problems.append(
            "page spec has no 'rows'"
            + (" (did you mean type: scene?)" if "scene" in spec else "")
        )
        return problems
    _check_tail_keys(spec.get("bubble_style") or {}, "bubble_style", problems)
    for ri, row in enumerate(rows):
        _check_row_height(row, f"r{ri}", problems)
        panels = row.get("panels")
        if not panels:
            problems.append(f"r{ri}: row has no 'panels'")
            continue
        for ci, panel in enumerate(panels):
            where = f"r{ri}c{ci}"
            _check_keys(panel, _PANEL_KEYS, "panel", where, problems)
            _check_panel(panel, libs, where, problems, spec_dir)
    return problems
