"""Render a comic spec (dict or YAML) into SVG, PNG, and PDF.

Spec shape (all panel-relative coords are fractions 0..1 of the panel):

    title: "..."                     # optional caption strip at top
    title_style: {font_size: 26, color: "#21304a", font: "..."}
    page: A4                         # A4 (default) or [w_mm, h_mm]
    bg: "#ffffff"                    # paper colour
    px_per_mm: 4                     # render scale
    margin_mm: 12
    gutter_mm: 5
    frame:                           # panel outline, page-wide (panel `frame:`
      width: 3.5                     # overrides); width 0 = no outline
      color: "#21304a"
      radius: 10                     # corner radius, also clips the art
    bubble_style:                    # page-wide bubble look, see bubbles.DEFAULT_STYLE
      font_size: 16
      pad: 14
      stroke_width: 3
      radius: 18
      uppercase: false
    library: "../characters"   # path to character dir
    scenes_dir: "../scenes"    # path to scenes dir
    pixel_dir: "../pixel"      # path to pixel-art dir
    rows:
      - height: 1.0                  # relative weight (optional, default 1)
                                     # or `height_mm: 60` for a fixed height;
                                     # weighted rows share what fixed rows leave
        panels:
          - bg: "#fbfaf6"            # optional panel background
            image: "art/01.png"      # optional raster background, scaled to
                                     # cover the panel; or {src:, fit:}
            actors:
              - char: tom
                pose: walk           # optional; defaults to character's default
                face: happy          # any slot -> variant
                arms: wave
                x: 0.35  y: 0.62     # centre, panel fraction
                scale: 0.85          # height as fraction of panel height
                flip: false
            pixel:                   # optional, one per panel (or a list)
              - art: heart
                x: 0.8  y: 0.25  scale: 0.18
            bubbles:
              - text: "Ahoj!"
                kind: speech         # speech | thought | shout
                speaker: tom         # auto-place above this actor + aim the tail
                                     # at their head; overrides below are optional
                at: tr               # corner/edge to hug: t/b/c x l/r/c (tl, tr,
                                     # bl, br, t, b, l, r, c); overrides x/y
                x: 0.5  y: 0.2       # explicit centre (else derived from speaker)
                to: [0.4, 0.5]       # explicit tail target (else the speaker's head)

When several bubbles in a panel omit `y`, they stack downward from the top,
each placed below the measured height of the one before it, so they never
overlap however long the text is; omit `x` too and each sits above its own
speaker (or in the middle, when there is no speaker — as on a raster panel).
`at:` picks a corner or edge instead; a bubble only stacks under (or, from the
bottom, over) the earlier bubbles it would actually overlap, so `tl` and `tr`
sit side by side when they fit and `bl` climbs up from the bottom. Every
bubble is then nudged to stay inside its panel.

PATH RESOLUTION
Relative paths in the spec (``library:``, ``scenes_dir:``, ``pixel_dir:``) are
resolved against the **spec file's directory** when the spec is loaded via a
path.  CLI flags and absolute paths are used as-is.  A panel's ``image:`` path
resolves the same way.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import cairosvg
import yaml

from . import pixelart, raster
from .bubbles import FONT, INK, bubble, bubble_size, resolve_style
from .library import Library
from .pixelart import PixelLibrary
from .scene import Scene, SceneLibrary
from .scene import cover as scene_cover

PAGE = {"A4": (210, 297), "A5": (148, 210), "letter": (216, 279)}


def load_spec(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


SPEC_TYPES = ("page", "scene")


def spec_type(spec: dict) -> str:
    """Return ``'page'`` or ``'scene'`` for a spec.

    A ``page`` is a comic grid (``rows`` of ``panels``, rendered with
    ``comicforge render``); a ``scene`` is a single illustration filling the
    canvas (top-level ``scene``, rendered with ``comicforge scene``).

    An explicit ``type:`` key wins; otherwise the type is inferred from
    structure (a top-level background — ``scene`` or ``image`` — and no ``rows``
    == a scene), so specs written before ``type:`` existed keep working.
    """
    declared = spec.get("type")
    if declared is not None:
        if declared not in SPEC_TYPES:
            raise ValueError(
                f"unknown spec type {declared!r}; use one of {list(SPEC_TYPES)}"
            )
        return declared
    has_bg = "scene" in spec or "image" in spec
    return "scene" if has_bg and "rows" not in spec else "page"


def _resolve_dir(value: str | Path | None, spec_dir: Path | None) -> Path | None:
    """Resolve an asset-dir value that may be relative.

    If *value* is a relative path and *spec_dir* is known, it is resolved
    against *spec_dir*.  Absolute paths and ``None`` are returned unchanged.
    """
    if value is None:
        return None
    p = Path(value)
    if not p.is_absolute() and spec_dir is not None:
        return (spec_dir / p).resolve()
    return p


def _require_dir(path: Path | None, label: str) -> Path:
    """Raise a clear error when a required asset directory is missing."""
    if path is None:
        raise ValueError(
            f"{label} directory is required but was not provided. "
            f"Set '{label}:' in the spec or pass the corresponding CLI flag."
        )
    if not path.is_dir():
        raise ValueError(f"{label} directory does not exist: {path}")
    return path


class _NullSceneLibrary:
    """Placeholder used when no scenes_dir is configured."""

    def get(self, name: str) -> Scene:
        raise KeyError(
            f"scene '{name}' requested but no scenes_dir was provided. "
            "Set 'scenes_dir:' in the spec or pass --scenes on the CLI."
        )

    def manifest(self) -> dict:
        return {}


def _panels(rows, x0, y0, W, H, gutter, k=1.0):
    """Yield (row_idx, col_idx, panel_dict, px, py, pw, ph).

    A row with ``height_mm`` is that tall (times *k* px/mm); the other rows
    share whatever height is left by their ``height`` weight. When every row
    is fixed the remainder of the page stays blank.
    """
    fixed = {ri: r["height_mm"] * k for ri, r in enumerate(rows) if "height_mm" in r}
    wsum = sum(r.get("height", 1) for ri, r in enumerate(rows) if ri not in fixed)
    avail_h = H - gutter * (len(rows) - 1) - sum(fixed.values())
    cy = y0
    for ri, row in enumerate(rows):
        ph = fixed[ri] if ri in fixed else avail_h * row.get("height", 1) / wsum
        cols = row["panels"]
        cw_sum = sum(c.get("width", 1) for c in cols)
        avail_w = W - gutter * (len(cols) - 1)
        cx = x0
        for ci, panel in enumerate(cols):
            pw = avail_w * panel.get("width", 1) / cw_sum
            yield ri, ci, panel, cx, cy, pw, ph
            cx += pw + gutter
        cy += ph + gutter


def _build_libs(
    spec: dict,
    spec_dir: Path | None,
    library: Library | None,
    scenes: SceneLibrary | _NullSceneLibrary | None,
    pixel_library: PixelLibrary | None,
) -> tuple[Library, SceneLibrary | _NullSceneLibrary, PixelLibrary | None]:
    """Resolve / build the three asset libraries from spec keys + overrides."""
    if library is None:
        lib_path = _resolve_dir(spec.get("library"), spec_dir)
        lib_path = _require_dir(lib_path, "library")
        library = Library(lib_path)
    if scenes is None:
        sc_path = _resolve_dir(spec.get("scenes_dir"), spec_dir)
        # scenes are optional — only required when a panel actually uses a scene
        scenes = SceneLibrary(sc_path) if sc_path is not None else _NullSceneLibrary()
    if pixel_library is None:
        px_path = _resolve_dir(spec.get("pixel_dir"), spec_dir)
        if px_path is not None:
            pixel_library = PixelLibrary(px_path)
        # else remains None — inline {grid, palette} still works
    return library, scenes, pixel_library


def build_svg(
    spec: dict,
    library: Library | None = None,
    scenes: SceneLibrary | None = None,
    pixel_library: PixelLibrary | None = None,
    spec_dir: Path | None = None,
) -> str:
    if spec_type(spec) == "scene":
        raise ValueError(
            "this is a 'scene' spec (single illustration) — render it with "
            "`comicforge scene` instead of `render`."
        )
    lib, scn, pxlib = _build_libs(spec, spec_dir, library, scenes, pixel_library)
    page = spec.get("page", "A4")
    w_mm, h_mm = PAGE[page] if isinstance(page, str) else page
    k = spec.get("px_per_mm", 4)
    W, H = w_mm * k, h_mm * k
    margin = spec.get("margin_mm", 12) * k
    gutter = spec.get("gutter_mm", 5) * k

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{spec.get("bg", "#ffffff")}"/>',
    ]

    top = margin
    title = spec.get("title")
    if title:
        tst = _title_style(spec)
        ts = tst["font_size"]
        parts.append(
            f'<text x="{W / 2}" y="{margin + ts}" text-anchor="middle" '
            f'font-family="{tst["font"]}" font-size="{ts}" font-weight="bold" '
            f'fill="{tst["color"]}">{escape(title)}</text>'
        )
        top = margin + ts + 14

    grid_x, grid_y = margin, top
    grid_w, grid_h = W - 2 * margin, H - top - margin

    for _ri, _ci, panel, px, py, pw, ph in _panels(
        spec["rows"], grid_x, grid_y, grid_w, grid_h, gutter, k
    ):
        parts.append(
            _render_panel(
                panel,
                px,
                py,
                pw,
                ph,
                lib,
                scn,
                pxlib,
                bubble_style=spec.get("bubble_style"),
                frame=spec.get("frame"),
                spec_dir=spec_dir,
            )
        )

    parts.append("</svg>")
    return "\n".join(parts)


TITLE_STYLE = {"font_size": 26, "color": INK, "font": FONT}


def _title_style(spec, font_size=TITLE_STYLE["font_size"]) -> dict:
    return {**TITLE_STYLE, "font_size": font_size, **(spec.get("title_style") or {})}


def _layout(spec):
    """Yield (row, col, panel, px, py, pw, ph) for every panel, using the same
    page metrics as build_svg."""
    page = spec.get("page", "A4")
    w_mm, h_mm = PAGE[page] if isinstance(page, str) else page
    k = spec.get("px_per_mm", 4)
    W, H = w_mm * k, h_mm * k
    margin = spec.get("margin_mm", 12) * k
    gutter = spec.get("gutter_mm", 5) * k
    top = margin + (_title_style(spec)["font_size"] + 14 if spec.get("title") else 0)
    yield from _panels(
        spec["rows"], margin, top, W - 2 * margin, H - top - margin, gutter, k
    )


def build_panel_svg(
    spec,
    row,
    col,
    library=None,
    scenes=None,
    scale=1.0,
    pixel_library=None,
    spec_dir=None,
) -> str:
    """Render a single panel standalone, at `scale` x its full-page pixel size
    (use scale < 1 for a quick low-res review render)."""
    lib, scn, pxlib = _build_libs(spec, spec_dir, library, scenes, pixel_library)
    for ri, ci, panel, _px, _py, pw, ph in _layout(spec):
        if ri == row and ci == col:
            # Render the panel body at full page size so absolute-sized elements
            # (bubble text) keep the same proportions as the whole-page render;
            # `scale` only shrinks the rasterized output via width/height, leaving
            # the viewBox full-size so everything scales uniformly.
            ow, oh = pw * scale, ph * scale
            body = _render_panel(
                panel,
                0,
                0,
                pw,
                ph,
                lib,
                scn,
                pxlib,
                bubble_style=spec.get("bubble_style"),
                frame=spec.get("frame"),
                spec_dir=spec_dir,
            )
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow:.0f}" '
                f'height="{oh:.0f}" viewBox="0 0 {pw:.1f} {ph:.1f}">\n'
                f"{body}\n</svg>"
            )
    raise ValueError(f"no panel at row {row}, col {col}")


def _scene_canvas(spec, scn, spec_dir) -> tuple[float, float]:
    """Canvas size for a standalone scene spec, from its scene or its image."""
    sc = spec.get("scene")
    if sc is not None:
        scene = scn.get(sc if isinstance(sc, str) else sc["name"])
        scale = spec.get("scale", 4)
        return scene.w * scale, scene.h * scale
    img = spec.get("image")
    if img is None:
        raise ValueError("a scene spec needs a background: set 'scene:' or 'image:'.")
    iw, ih = raster.size(raster.resolve(img, spec_dir))
    scale = spec.get("scale", 1)
    return iw * scale, ih * scale


def build_scene_svg(
    spec: dict,
    library: Library | None = None,
    scenes: SceneLibrary | None = None,
    pixel_library: PixelLibrary | None = None,
    spec_dir: Path | None = None,
) -> str:
    """Render a standalone illustration: one scene filling the whole canvas,
    with actors / pixel art / bubbles on top. No comic grid, no panel border.

    The background is either a vector ``scene`` (name or
    {name, <slot>: <variant>}) sized at ``scale`` px per scene unit (default 4),
    or a raster ``image`` sized at ``scale`` output px per image px (default 1).
    On top of it go ``actors`` / ``pixel`` / ``bubbles`` like a single panel,
    plus an optional ``title`` and ``bubble_style`` (see ``_render_panel``).
    """
    if spec_type(spec) == "page":
        raise ValueError(
            "this is a 'page' spec (comic grid) — render it with "
            "`comicforge render` instead of `scene`."
        )
    lib, scn, pxlib = _build_libs(spec, spec_dir, library, scenes, pixel_library)
    w, h = _scene_canvas(spec, scn, spec_dir)
    body = _render_panel(
        spec,
        0,
        0,
        w,
        h,
        lib,
        scn,
        pxlib,
        border=False,
        bubble_style=spec.get("bubble_style"),
        spec_dir=spec_dir,
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        body,
    ]
    title = spec.get("title")
    if title:
        tst = _title_style(spec, font_size=22)
        ts = tst["font_size"]
        parts.append(
            f'<text x="{w / 2}" y="{ts + 8}" text-anchor="middle" '
            f'font-family="{tst["font"]}" font-size="{ts}" font-weight="bold" '
            f'fill="{tst["color"]}">{escape(title)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def build_character_svg(
    name: str,
    selection: dict[str, str],
    pose: str | None = None,
    *,
    library: Library,
    scale: float = 2.0,
    bg: str = "#ffffff",
    flip: bool = False,
    pad: float = 0.08,
) -> str:
    """Render one character standalone, cropped to its pose, for quick review.

    No page, no panel grid — just the composed character on a `bg` canvas sized
    to the pose's viewBox times `scale`, with a `pad` fraction of margin.
    """
    char = library.get(name)
    p = char.resolve_pose(pose)
    bw, bh = p.w * scale, p.h * scale
    m = max(bw, bh) * pad
    w, h = bw + 2 * m, bh + 2 * m
    inner = char.place(selection, cx=w / 2, cy=h / 2, height=bh, flip=flip, pose=pose)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
        f'viewBox="0 0 {w:.1f} {h:.1f}">\n'
        f'<rect width="{w:.1f}" height="{h:.1f}" fill="{bg}"/>\n'
        f"{inner}\n</svg>"
    )


def render_character(
    name: str,
    out_path: str | Path,
    selection: dict[str, str],
    pose: str | None = None,
    *,
    library: Library,
    scale: float = 2.0,
    bg: str = "#ffffff",
    flip: bool = False,
) -> str:
    """Render a single character to .svg/.png/.pdf for review. Returns the SVG."""
    return _write(
        build_character_svg(
            name, selection, pose, library=library, scale=scale, bg=bg, flip=flip
        ),
        out_path,
    )


# Panel outline defaults; a page's `frame:` (and a panel's) override any key.
FRAME: dict[str, Any] = {"width": 3.5, "color": INK, "radius": 10}

# Bubble auto-layout: how far from a panel edge a bubble is kept, and the gap
# left between two bubbles that stack because neither declared a `y`.
BUBBLE_INSET = 8.0
BUBBLE_GAP = 10.0


def _clamp(centre, size, origin, extent):
    """Keep a bubble of *size* inside [origin, origin+extent], centring it when
    it is too big to fit."""
    if size + 2 * BUBBLE_INSET >= extent:
        return origin + extent / 2
    lo = origin + BUBBLE_INSET + size / 2
    hi = origin + extent - BUBBLE_INSET - size / 2
    return min(max(centre, lo), hi)


# `at:` anchors — (column, edge). A column is l / c / r, an edge t / b, or c
# for "vertically centred, no stacking".
ANCHORS = {
    "tl": ("l", "t"), "t": ("c", "t"), "tc": ("c", "t"), "tr": ("r", "t"),
    "bl": ("l", "b"), "b": ("c", "b"), "bc": ("c", "b"), "br": ("r", "b"),
    "l": ("l", "c"), "c": ("c", "c"), "r": ("r", "c"), "cl": ("l", "c"),
    "cr": ("r", "c"),
}  # fmt: skip


def _anchor(at):
    if at is None:
        return "c", "t"
    if at not in ANCHORS:
        raise ValueError(f"unknown bubble anchor {at!r}; use one of {sorted(ANCHORS)}")
    return ANCHORS[at]


def _stack(edge, bx, bw, bh, placed, py, ph):
    """Vertical centre for a bubble of width *bw* / height *bh* centred on
    *bx*: `t` sits as high as it can, `b` as low as it can, moving past any
    bubble already *placed* (list of (x0, y0, x1, y1) boxes) that it would
    overlap; `c` sits in the middle of the panel."""
    if edge == "c":
        return py + ph / 2
    x0, x1 = bx - bw / 2, bx + bw / 2
    top = py + ph - BUBBLE_INSET - bh if edge == "b" else py + BUBBLE_INSET
    moved = True
    while moved:
        moved = False
        for bx0, by0, bx1, by1 in placed:
            if bx0 < x1 and bx1 > x0 and by0 < top + bh and by1 > top:
                top = by0 - BUBBLE_GAP - bh if edge == "b" else by1 + BUBBLE_GAP
                moved = True
    return top + bh / 2


def _tail_target(b, actor):
    """Tail target in panel fractions: explicit `to`, else the speaker's head."""
    to = b.get("to")
    if to is None and actor is not None:
        to = [
            actor.get("x", 0.5),
            max(actor.get("y", 0.6) - actor.get("scale", 0.8) * 0.42, 0.05),
        ]
    return to


def _render_bubbles(panel, px, py, pw, ph, bubble_style) -> list[str]:
    """Draw a panel's bubbles on top of everything else.

    Placement can be derived from a bubble's `speaker`; on a raster panel there
    are no actors, so a bubble with no `x`/`y` is centred horizontally and
    stacked below the measured bottom of the previous one. `at:` moves a bubble
    to a corner or edge instead; each column keeps its own top and bottom
    stack so bubbles that share a corner never overlap.
    """
    actors_by_char = {}
    for a in panel.get("actors", []):
        actors_by_char.setdefault(a["char"], a)
    style = resolve_style(bubble_style)

    def ax(fx):  # panel fraction -> page px
        return px + fx * pw

    def ay(fy):
        return py + fy * ph

    out = []
    placed = []  # (x0, y0, x1, y1) of every bubble drawn so far, for stacking
    for b in panel.get("bubbles", []):
        actor = actors_by_char.get(b.get("speaker")) if b.get("speaker") else None
        to = _tail_target(b, actor)
        tail = (ax(to[0]), ay(to[1])) if to else None
        text = b["text"]
        if b.get("uppercase", style["uppercase"]):
            text = text.upper()
        kind = b.get("kind", "speech")
        max_chars = b.get("max_chars", 22)
        fs = b.get("fs", style["font_size"])
        bw, bh = bubble_size(text, kind, max_chars, fs, style=style)
        col, edge = _anchor(b.get("at"))
        # centre: explicit x/y, else the anchor column / above the speaker
        if b.get("x") is not None:
            bx = ax(b["x"])
        elif col == "c":
            bx = ax(actor["x"] if actor and "x" in actor else 0.5)
        elif col == "l":
            bx = px + BUBBLE_INSET + bw / 2
        else:
            bx = px + pw - BUBBLE_INSET - bw / 2
        bx = _clamp(bx, bw, px, pw)
        if b.get("y") is not None:
            by = ay(b["y"])
        else:
            by = _stack(edge, bx, bw, bh, placed, py, ph)
        by = _clamp(by, bh, py, ph)
        placed.append((bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2))
        out.append(
            bubble(
                text,
                bx,
                by,
                tail=tail,
                kind=kind,
                max_chars=max_chars,
                fs=fs,
                style=style,
            )
        )
    return out


def _render_panel(
    panel,
    px,
    py,
    pw,
    ph,
    lib,
    scenes,
    pixel_library=None,
    border=True,
    bubble_style=None,
    frame=None,
    spec_dir=None,
) -> str:
    bg = panel.get("bg", "#fbfaf6")
    fr = {**FRAME, **(frame or {}), **(panel.get("frame") or {})}
    clip = f"clip{int(px)}_{int(py)}"
    out = [
        f'<clipPath id="{clip}"><rect x="{px:.1f}" y="{py:.1f}" '
        f'width="{pw:.1f}" height="{ph:.1f}" rx="{fr["radius"]}"/></clipPath>',
        f'<g clip-path="url(#{clip})">',
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
        f'fill="{bg}"/>',
    ]

    def ax(fx):  # panel fraction -> page px
        return px + fx * pw

    def ay(fy):
        return py + fy * ph

    # raster background (under everything; the clip path crops the overflow)
    img = panel.get("image")
    if img is not None:
        out.append(raster.place(img, spec_dir, px, py, pw, ph))

    # scene background (over a raster image, if both are given)
    sc = panel.get("scene")
    if sc is not None:
        if isinstance(sc, str):
            sc = {"name": sc}
        scene = scenes.get(sc["name"])
        selection = {s: sc[s] for s in scene.slots if s in sc}
        out.append(scene_cover(scene, selection, px, py, pw, ph))

    # pixel art (background-ish, drawn before characters)
    for spec in _as_list(panel.get("pixel")):
        inner, cols, rows = pixelart.resolve(spec, pixel_library)
        height = spec.get("scale", 0.2) * ph
        cell = height / rows
        w = cols * cell
        cx = ax(spec.get("x", 0.5)) - w / 2
        cy = ay(spec.get("y", 0.5)) - height / 2
        out.append(
            f'<g transform="translate({cx:.1f},{cy:.1f}) scale({cell:.3f})">{inner}</g>'
        )

    # actors
    for a in panel.get("actors", []):
        char = lib.get(a["char"])
        pose = a.get("pose")
        selection = {s: a[s] for s in char.slots_for(pose) if s in a}
        out.append(
            char.place(
                selection,
                cx=ax(a.get("x", 0.5)),
                cy=ay(a.get("y", 0.6)),
                height=a.get("scale", 0.8) * ph,
                flip=a.get("flip", False),
                pose=pose,
            )
        )

    out.extend(_render_bubbles(panel, px, py, pw, ph, bubble_style))

    out.append("</g>")
    # crisp panel border on top of clipped content
    if border and fr["width"] > 0:
        out.append(
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
            f'rx="{fr["radius"]}" fill="none" stroke="{fr["color"]}" '
            f'stroke-width="{fr["width"]}"/>'
        )
    return "\n".join(out)


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _write(svg: str, out_path: str | Path) -> str:
    out_path = Path(out_path)
    ext = out_path.suffix.lower()
    if ext == ".svg":
        out_path.write_text(svg, encoding="utf-8")
    elif ext == ".png":
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out_path))
    elif ext == ".pdf":
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=str(out_path))
    else:
        raise ValueError(f"unsupported output extension: {ext}")
    return svg


def _load(spec):
    """Normalise a spec arg to (dict, spec_dir). Paths resolve against the spec
    file's dir; an inline dict has no dir."""
    if isinstance(spec, dict):
        return spec, None
    spec_path = Path(spec)
    return load_spec(spec_path), spec_path.parent.resolve()


def render_spec(
    spec,
    out_path: str | Path,
    library=None,
    scenes=None,
    pixel_library=None,
):
    """Render a comic page to .svg/.png/.pdf by extension. Returns the SVG."""
    spec, spec_dir = _load(spec)
    return _write(
        build_svg(spec, library, scenes, pixel_library, spec_dir=spec_dir),
        out_path,
    )


def render_panel(
    spec,
    out_path,
    row=0,
    col=0,
    library=None,
    scenes=None,
    scale=0.5,
    pixel_library=None,
):
    """Render one panel to .svg/.png/.pdf for review. Returns the SVG."""
    spec, spec_dir = _load(spec)
    return _write(
        build_panel_svg(
            spec, row, col, library, scenes, scale, pixel_library, spec_dir=spec_dir
        ),
        out_path,
    )


def render_all_panels(
    spec,
    out_dir,
    library=None,
    scenes=None,
    scale=0.5,
    ext=".png",
    pixel_library=None,
):
    """Render every panel into out_dir as panel_r<R>c<C>.<ext>. Returns paths."""
    spec, spec_dir = _load(spec)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    for ri, ci, *_ in _layout(spec):
        p = out_dir / f"panel_r{ri}c{ci}{ext}"
        _write(
            build_panel_svg(
                spec, ri, ci, library, scenes, scale, pixel_library, spec_dir=spec_dir
            ),
            p,
        )
        outs.append(p)
    return outs


def render_scene(
    spec,
    out_path: str | Path,
    library=None,
    scenes=None,
    pixel_library=None,
):
    """Render a standalone scene illustration. Returns the SVG."""
    spec, spec_dir = _load(spec)
    return _write(
        build_scene_svg(spec, library, scenes, pixel_library, spec_dir=spec_dir),
        out_path,
    )
