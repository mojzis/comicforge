"""Render a comic spec (dict or YAML) into SVG, PNG, and PDF.

Spec shape (all panel-relative coords are fractions 0..1 of the panel):

    title: "..."                     # optional caption strip at top
    page: A4                         # A4 (default) or [w_mm, h_mm]
    px_per_mm: 4                     # render scale
    margin_mm: 12
    gutter_mm: 5
    library: "../characters"   # path to character dir
    scenes_dir: "../scenes"    # path to scenes dir
    pixel_dir: "../pixel"      # path to pixel-art dir
    rows:
      - height: 1.0                  # relative weight (optional, default 1)
        panels:
          - bg: "#fbfaf6"            # optional panel background
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
                x: 0.5  y: 0.2       # explicit centre (else derived from speaker)
                to: [0.4, 0.5]       # explicit tail target (else the speaker's head)

When several bubbles in a panel omit `y`, they stack downward from the top so
they never overlap; omit `x` too and each sits above its own speaker.

PATH RESOLUTION
Relative paths in the spec (``library:``, ``scenes_dir:``, ``pixel_dir:``) are
resolved against the **spec file's directory** when the spec is loaded via a
path.  CLI flags and absolute paths are used as-is.
"""

from __future__ import annotations

from pathlib import Path

import cairosvg
import yaml

from . import pixelart
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
    structure (top-level ``scene`` and no ``rows`` == a scene), so specs written
    before ``type:`` existed keep working.
    """
    declared = spec.get("type")
    if declared is not None:
        if declared not in SPEC_TYPES:
            raise ValueError(
                f"unknown spec type {declared!r}; use one of {list(SPEC_TYPES)}"
            )
        return declared
    return "scene" if "scene" in spec and "rows" not in spec else "page"


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


def _panels(rows, x0, y0, W, H, gutter):
    """Yield (row_idx, col_idx, panel_dict, px, py, pw, ph)."""
    wsum = sum(r.get("height", 1) for r in rows)
    avail_h = H - gutter * (len(rows) - 1)
    cy = y0
    for ri, row in enumerate(rows):
        ph = avail_h * row.get("height", 1) / wsum
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
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
    ]

    top = margin
    title = spec.get("title")
    if title:
        ts = 26
        parts.append(
            f'<text x="{W / 2}" y="{margin + ts}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{ts}" font-weight="bold" '
            f'fill="{INK}">{title}</text>'
        )
        top = margin + ts + 14

    grid_x, grid_y = margin, top
    grid_w, grid_h = W - 2 * margin, H - top - margin

    for _ri, _ci, panel, px, py, pw, ph in _panels(
        spec["rows"], grid_x, grid_y, grid_w, grid_h, gutter
    ):
        parts.append(_render_panel(panel, px, py, pw, ph, lib, scn, pxlib))

    parts.append("</svg>")
    return "\n".join(parts)


def _layout(spec):
    """Yield (row, col, panel, px, py, pw, ph) for every panel, using the same
    page metrics as build_svg."""
    page = spec.get("page", "A4")
    w_mm, h_mm = PAGE[page] if isinstance(page, str) else page
    k = spec.get("px_per_mm", 4)
    W, H = w_mm * k, h_mm * k
    margin = spec.get("margin_mm", 12) * k
    gutter = spec.get("gutter_mm", 5) * k
    top = margin + (26 + 14 if spec.get("title") else 0)
    yield from _panels(
        spec["rows"], margin, top, W - 2 * margin, H - top - margin, gutter
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
            body = _render_panel(panel, 0, 0, pw, ph, lib, scn, pxlib)
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow:.0f}" '
                f'height="{oh:.0f}" viewBox="0 0 {pw:.1f} {ph:.1f}">\n'
                f"{body}\n</svg>"
            )
    raise ValueError(f"no panel at row {row}, col {col}")


def build_scene_svg(
    spec: dict,
    library: Library | None = None,
    scenes: SceneLibrary | None = None,
    pixel_library: PixelLibrary | None = None,
    spec_dir: Path | None = None,
) -> str:
    """Render a standalone illustration: one scene filling the whole canvas,
    with actors / pixel art / bubbles on top. No comic grid, no panel border.

    Spec shape: ``scene`` (name or {name, <slot>: <variant>}), optional
    ``scale`` (px per scene unit, default 4), plus ``actors`` / ``pixel`` /
    ``bubbles`` like a single panel, and an optional ``title``.
    """
    if spec_type(spec) == "page":
        raise ValueError(
            "this is a 'page' spec (comic grid) — render it with "
            "`comicforge render` instead of `scene`."
        )
    lib, scn, pxlib = _build_libs(spec, spec_dir, library, scenes, pixel_library)
    sc = spec["scene"]
    name = sc if isinstance(sc, str) else sc["name"]
    scene = scn.get(name)
    scale = spec.get("scale", 4)
    w, h = scene.w * scale, scene.h * scale
    body = _render_panel(spec, 0, 0, w, h, lib, scn, pxlib, border=False)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        body,
    ]
    title = spec.get("title")
    if title:
        ts = 22
        parts.append(
            f'<text x="{w / 2}" y="{ts + 8}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{ts}" font-weight="bold" '
            f'fill="{INK}">{title}</text>'
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


def _render_panel(
    panel, px, py, pw, ph, lib, scenes, pixel_library=None, border=True
) -> str:
    bg = panel.get("bg", "#fbfaf6")
    clip = f"clip{int(px)}_{int(py)}"
    out = [
        f'<clipPath id="{clip}"><rect x="{px:.1f}" y="{py:.1f}" '
        f'width="{pw:.1f}" height="{ph:.1f}" rx="10"/></clipPath>',
        f'<g clip-path="url(#{clip})">',
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
        f'fill="{bg}"/>',
    ]

    def ax(fx):  # panel fraction -> page px
        return px + fx * pw

    def ay(fy):
        return py + fy * ph

    # scene background (under everything)
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

    # bubbles (on top) — placement can be derived from `speaker`
    actors_by_char = {}
    for a in panel.get("actors", []):
        actors_by_char.setdefault(a["char"], a)
    auto_y = 0  # how many bubbles we've auto-stacked from the top
    for b in panel.get("bubbles", []):
        actor = actors_by_char.get(b.get("speaker")) if b.get("speaker") else None
        # tail target: explicit `to`, else the speaker's head
        to = b.get("to")
        if to is None and actor is not None:
            to = [
                actor.get("x", 0.5),
                max(actor.get("y", 0.6) - actor.get("scale", 0.8) * 0.42, 0.05),
            ]
        tail = (ax(to[0]), ay(to[1])) if to else None
        # centre: explicit x/y, else above the speaker, stacked to avoid overlap
        bx_f = b.get("x")
        if bx_f is None:
            bx_f = min(max(actor.get("x", 0.5), 0.24), 0.76) if actor else 0.5
        by_f = b.get("y")
        if by_f is None:
            by_f = min(0.15 + 0.17 * auto_y, 0.6)
            auto_y += 1
        out.append(
            bubble(
                b["text"],
                ax(bx_f),
                ay(by_f),
                tail=tail,
                kind=b.get("kind", "speech"),
                max_chars=b.get("max_chars", 22),
                fs=b.get("fs", 16),
            )
        )

    out.append("</g>")
    # crisp panel border on top of clipped content
    if border:
        out.append(
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
            f'rx="10" fill="none" stroke="{INK}" stroke-width="3.5"/>'
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
