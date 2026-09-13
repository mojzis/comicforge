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
    caption_style:                   # page-wide caption look, see caption.DEFAULT_STYLE
      font_size: 13
      pad: 8
      max_chars: 60
      align: left                    # left | center
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
                                     # or `height_mm: 60` for a fixed height,
                                     # or `height: auto` to size the row from its
                                     # images + captions (squeezed to fit the page);
                                     # weighted rows share what the others leave
        panels:
          - bg: "#fbfaf6"            # optional panel background
            caption: "Rain came."    # narration band under the art, inside
                                     # the frame; or {text:, max_chars:}
            image: "art/01.png"      # optional raster background, scaled to
                                     # cover the panel; or {src:, fit:, at:,
                                     # crop: {top:, bottom:, left:, right:}}
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
                speaker: tom         # an actor's char, or a `speakers:` name:
                                     # aligns the bubble + aims the tail there
                at: tr               # corner/edge to hug: t/b/c x l/r/c (tl, tr,
                                     # bl, br, t, b, l, r, c); overrides x/y
                x: 0.5  y: 0.2       # explicit centre (else derived from speaker)
                to: [0.4, 0.5]       # explicit tail target (else the speaker's head)
                tail_from: b         # where the tail leaves: edge t/b/l/r, a
                                     # position 0..1 along it, or {edge:, pos:}
                tail: curve          # wedge (default) | curve | line | none
                tail_bend: 0.4       # curve/line: -1..1, 0 straight (else auto)
            speakers:                # head positions for panels without actors
              ema: [0.72, 0.3]       # (e.g. raster art), panel fractions

When several bubbles in a panel omit `y`, they stack downward from the top,
each placed below the measured height of the one before it, so they never
overlap however long the text is; omit `x` too and each sits above its own
speaker (or in the middle, when there is no speaker — as on a raster panel).
On a panel with `speakers:`, a bubble with a `speaker` and no `x`/`y`/`at` is
placed in reading order instead: on its speaker's side, its top clearly below
the previous bubble's, keeping clear of speaker points and earlier tails.
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

from . import caption, layout, pixelart, raster
from .bubbles import FONT, INK, bubble
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


def _panel_widths(panels, W, gutter) -> list[float]:
    """Width of every panel in a row: ``width`` weights sharing *W* after gutters."""
    total = sum(p.get("width", 1) for p in panels)
    avail = W - gutter * (len(panels) - 1)
    return [avail * p.get("width", 1) / total for p in panels]


def _auto_parts(row, W, gutter, caption_style, spec_dir) -> list[tuple[float, float]]:
    """(art_px, caption_band_px) per panel of a ``height: auto`` row: the art is
    as tall as the panel's image (after ``crop:``) wants at the panel's width."""
    parts = []
    widths = _panel_widths(row["panels"], W, gutter)
    for panel, pw in zip(row["panels"], widths, strict=True):
        img = panel.get("image")
        art = 0.0
        if img is not None:
            _x, _y, iw, ih = raster.region(img, spec_dir)
            art = pw * ih / iw
        parts.append((art, caption.height(panel.get("caption"), caption_style, pw)))
    if not any(art for art, _band in parts):
        raise ValueError(
            "a `height: auto` row needs a panel with an `image:` to take its "
            "height from"
        )
    return parts


def _auto_height(parts, squeeze=1.0) -> float:
    """A ``height: auto`` row's height: tall enough for every panel's art
    (times *squeeze*) plus that panel's own caption band."""
    return max(squeeze * art + band for art, band in parts)


def _squeeze(autos, free) -> float:
    """The largest factor <= 1 the art of every auto row can be scaled by so
    the rows fit in *free* px. Caption bands never shrink."""
    if sum(_auto_height(parts) for parts in autos) <= free:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(40):  # total height is monotone in the factor: bisect
        mid = (lo + hi) / 2
        if sum(_auto_height(parts, mid) for parts in autos) <= free:
            lo = mid
        else:
            hi = mid
    return lo


def _row_heights(rows, W, H, gutter, k=1.0, caption_style=None, spec_dir=None):
    """(height in px of every row in a *W* x *H* grid, auto-row art squeeze).

    A row with ``height_mm`` is that tall (times *k* px/mm). A ``height: auto``
    row is as tall as its pictures want at their panel widths plus the caption
    bands; when the auto rows do not fit, their art is scaled down by one common
    factor until they do (``fit: cover`` then crops the excess, per the image's
    ``at:``). The remaining rows share whatever height is left by their
    ``height`` weight. When no row is weighted the remainder stays blank.
    """
    heights = {ri: r["height_mm"] * k for ri, r in enumerate(rows) if "height_mm" in r}
    autos = {
        ri: _auto_parts(r, W, gutter, caption_style, spec_dir)
        for ri, r in enumerate(rows)
        if ri not in heights and r.get("height") == "auto"
    }
    free = H - gutter * (len(rows) - 1) - sum(heights.values())
    squeeze = _squeeze(autos.values(), free)
    heights.update({ri: _auto_height(parts, squeeze) for ri, parts in autos.items()})
    weighted = [ri for ri in range(len(rows)) if ri not in heights]
    left = max(0.0, free - sum(heights[ri] for ri in autos))
    wsum = sum(rows[ri].get("height", 1) for ri in weighted)
    heights.update({ri: left * rows[ri].get("height", 1) / wsum for ri in weighted})
    return [heights[ri] for ri in range(len(rows))], squeeze


def _panels(rows, x0, y0, W, heights, gutter):
    """Yield (row_idx, col_idx, panel_dict, px, py, pw, ph) for rows of the
    given *heights* (see :func:`_row_heights`)."""
    cy = y0
    for ri, (row, ph) in enumerate(zip(rows, heights, strict=True)):
        cx = x0
        widths = _panel_widths(row["panels"], W, gutter)
        for ci, (panel, pw) in enumerate(zip(row["panels"], widths, strict=True)):
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
    W, H, _k, margin = _page_metrics(spec)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{spec.get("bg", "#ffffff")}"/>',
    ]

    title = spec.get("title")
    if title:
        tst = _title_style(spec)
        ts = tst["font_size"]
        parts.append(
            f'<text x="{W / 2}" y="{margin + ts}" text-anchor="middle" '
            f'font-family="{tst["font"]}" font-size="{ts}" font-weight="bold" '
            f'fill="{tst["color"]}">{escape(title)}</text>'
        )

    for _ri, _ci, panel, px, py, pw, ph in _layout(spec, spec_dir):
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
                caption_style=spec.get("caption_style"),
                spec_dir=spec_dir,
            )
        )

    parts.append("</svg>")
    return "\n".join(parts)


TITLE_STYLE = {"font_size": 26, "color": INK, "font": FONT}


def _title_style(spec, font_size=TITLE_STYLE["font_size"]) -> dict:
    return {**TITLE_STYLE, "font_size": font_size, **(spec.get("title_style") or {})}


def _page_metrics(spec) -> tuple[float, float, float, float]:
    """(page width px, page height px, px per mm, margin px) of a page spec."""
    page = spec.get("page", "A4")
    w_mm, h_mm = PAGE[page] if isinstance(page, str) else page
    k = spec.get("px_per_mm", 4)
    return w_mm * k, h_mm * k, k, spec.get("margin_mm", 12) * k


def _grid(spec, spec_dir=None):
    """(grid x, grid y, grid width, gutter, row heights, squeeze) of a page spec.
    *spec_dir* resolves the images a ``height: auto`` row measures."""
    W, H, k, margin = _page_metrics(spec)
    gutter = spec.get("gutter_mm", 5) * k
    top = margin + (_title_style(spec)["font_size"] + 14 if spec.get("title") else 0)
    grid_w, grid_h = W - 2 * margin, H - top - margin
    heights, squeeze = _row_heights(
        spec["rows"], grid_w, grid_h, gutter, k, spec.get("caption_style"), spec_dir
    )
    return margin, top, grid_w, gutter, heights, squeeze


def _layout(spec, spec_dir=None):
    """Yield (row, col, panel, px, py, pw, ph) for every panel of a page spec."""
    x0, y0, grid_w, gutter, heights, _squeeze = _grid(spec, spec_dir)
    yield from _panels(spec["rows"], x0, y0, grid_w, heights, gutter)


def page_squeeze(spec, spec_dir: Path | None = None) -> float:
    """How much a page's ``height: auto`` rows have their art scaled to fit:
    ``1.0`` when they fit as they are, ``0.9`` when each picture loses a tenth
    of its height to the crop. Lets a caller paginate — start a new page when
    adding a row would squeeze past what it tolerates. *spec* is a dict or a
    path (then *spec_dir* defaults to its directory)."""
    if not isinstance(spec, dict):
        spec, spec_dir = _load(spec)
    return _grid(spec, spec_dir)[-1]


def _art_boxes(spec, spec_dir=None, scenes=None):
    """Yield (where, panel, art width px, art height px) for every panel of a
    page spec — ``where`` is ``r<R>c<C>`` — or once, as ``scene``, for a
    standalone scene spec. The art box is the panel less its caption band:
    what panel fractions are relative to."""
    cst = spec.get("caption_style")
    if spec_type(spec) == "scene":
        w, h = _scene_canvas(spec, scenes or _NullSceneLibrary(), spec_dir)
        yield "scene", spec, w, h - caption.height(spec.get("caption"), cst, w)
        return
    for ri, ci, panel, _px, _py, pw, ph in _layout(spec, spec_dir):
        art_h = ph - caption.height(panel.get("caption"), cst, pw)
        yield f"r{ri}c{ci}", panel, pw, art_h


def _fractions(xy, w, h) -> list[float]:
    return [round(xy[0] / w, 4), round(xy[1] / h, 4)]


def panel_bubble_layout(panel: dict, width, height, bubble_style=None) -> dict:
    """Bubble geometry of one *panel* dict whose art box is *width* x *height*
    px; see :func:`bubble_layout` for the shape of the result."""
    placements = layout.layout_bubbles(panel, 0, 0, width, height, bubble_style)
    points = layout.speaker_points(panel)

    def frac(xy):
        return _fractions(xy, width, height)

    bubbles = []
    for p in placements:
        x0, y0, x1, y1 = p.box
        tail = None
        if p.tail is not None:
            tail = {
                "edge": p.tail.edge,
                "shape": p.tail.shape,
                "bend": p.tail.bend,
                "start": frac(p.tail.start),
                "control": frac(p.tail.control),
                "tip": frac(p.tail.tip),
                "target": frac(p.tail.target),
            }
        bubbles.append(
            {
                "index": p.index,
                "text": p.text,
                "kind": p.kind,
                "speaker": p.speaker,
                "auto": p.auto,
                "center": frac(p.centre),
                "box": frac((x0, y0)) + frac((x1, y1)),
                "tail": tail,
            }
        )
    px_points = {n: (x * width, y * height) for n, (x, y) in points.items()}
    return {
        "width": round(width, 2),
        "height": round(height, 2),
        "speakers": {n: [round(x, 4), round(y, 4)] for n, (x, y) in points.items()},
        "bubbles": bubbles,
        "warnings": layout.layout_warnings(placements, px_points),
    }


def bubble_layout(spec, row: int = 0, col: int = 0, spec_dir=None) -> dict:
    """Where every bubble of one panel lands, without rendering.

    *spec* is a dict or a path (then *spec_dir* defaults to its directory); a
    standalone scene spec is its own single panel and ignores *row* / *col*.
    Returns a JSON-ready dict, every point in panel fractions of the art box
    (the panel less its caption band, as in the spec)::

        {"width": 640.0, "height": 412.5,          # art box, page px
         "speakers": {"ema": [0.7, 0.3]},          # resolved speaker points
         "bubbles": [{"index": 0, "text": "…", "kind": "speech",
                      "speaker": "ema", "auto": True,  # reading-order placed
                      "center": [x, y], "box": [x0, y0, x1, y1],
                      "tail": {"edge": "b", "shape": "wedge", "bend": 0.0,
                               "start": [x, y], "control": [x, y],
                               "tip": [x, y], "target": [x, y]} or None}],
                                                   # None: no target, or tail: none
         "warnings": ["…"]}                        # as `validate` reports them
    """
    if not isinstance(spec, dict):
        spec, spec_dir = _load(spec)
    sc_path = _resolve_dir(spec.get("scenes_dir"), spec_dir)
    scenes = SceneLibrary(sc_path) if sc_path is not None else _NullSceneLibrary()
    for where, panel, w, h in _art_boxes(spec, spec_dir, scenes):
        if where in ("scene", f"r{row}c{col}"):
            return panel_bubble_layout(panel, w, h, spec.get("bubble_style"))
    raise ValueError(f"no panel at row {row}, col {col}")


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
    for ri, ci, panel, _px, _py, pw, ph in _layout(spec, spec_dir):
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
                caption_style=spec.get("caption_style"),
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
    _x, _y, iw, ih = raster.region(img, spec_dir)
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
        caption_style=spec.get("caption_style"),
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


def _render_bubbles(panel, px, py, pw, ph, bubble_style) -> list[str]:
    """Draw a panel's bubbles on top of everything else, where
    :func:`layout.layout_bubbles` puts them."""
    return [
        bubble(
            p.text,
            *p.centre,
            tail=p.tail.target if p.tail else None,
            kind=p.kind,
            max_chars=p.max_chars,
            fs=p.fs,
            style=p.style,
        )
        for p in layout.layout_bubbles(panel, px, py, pw, ph, bubble_style)
    ]


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
    caption_style=None,
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
    # a caption band takes the bottom of the box; the art gets what is left,
    # so every panel-fraction coordinate below is relative to the picture
    cap = caption.normalize(panel.get("caption"))
    cst = caption.resolve_style(caption_style)
    box_h = ph
    if cap is not None:
        band_h = caption.height(cap, cst, pw)
        ph = ph - band_h
        out.append(
            caption.band(cap, cst, px, py + ph, pw, band_h, fr["color"], fr["width"])
        )

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
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{box_h:.1f}" '
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
    for ri, ci, *_ in _layout(spec, spec_dir):
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
