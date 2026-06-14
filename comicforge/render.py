"""Render a comic spec (dict or YAML) into SVG, PNG, and PDF.

Spec shape (all panel-relative coords are fractions 0..1 of the panel):

    title: "..."                     # optional caption strip at top
    page: A4                         # A4 (default) or [w_mm, h_mm]
    px_per_mm: 4                     # render scale
    margin_mm: 12
    gutter_mm: 5
    rows:
      - height: 1.0                  # relative weight (optional, default 1)
        panels:
          - bg: "#fbfaf6"            # optional panel background
            actors:
              - char: tom
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
                x: 0.5  y: 0.2
                to: [0.4, 0.5]       # tail target, panel fraction (optional)
"""
from __future__ import annotations
from pathlib import Path
import yaml
import cairosvg

from .library import Library
from .bubbles import bubble, FONT, INK
from . import pixelart

DEFAULT_LIB = Path(__file__).resolve().parent.parent / "characters"
PAGE = {"A4": (210, 297), "A5": (148, 210), "letter": (216, 279)}


def load_spec(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


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


def build_svg(spec: dict, library: Library | None = None) -> str:
    lib = library or Library(spec.get("library", DEFAULT_LIB))
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
            f'<text x="{W/2}" y="{margin + ts}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{ts}" font-weight="bold" '
            f'fill="{INK}">{title}</text>'
        )
        top = margin + ts + 14

    grid_x, grid_y = margin, top
    grid_w, grid_h = W - 2 * margin, H - top - margin

    for _ri, _ci, panel, px, py, pw, ph in _panels(
        spec["rows"], grid_x, grid_y, grid_w, grid_h, gutter
    ):
        parts.append(_render_panel(panel, px, py, pw, ph, lib))

    parts.append("</svg>")
    return "\n".join(parts)


def _render_panel(panel, px, py, pw, ph, lib) -> str:
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

    # pixel art (background-ish, drawn before characters)
    for spec in _as_list(panel.get("pixel")):
        inner, cols, rows = pixelart.resolve(spec)
        height = spec.get("scale", 0.2) * ph
        cell = height / rows
        w = cols * cell
        cx = ax(spec.get("x", 0.5)) - w / 2
        cy = ay(spec.get("y", 0.5)) - height / 2
        out.append(f'<g transform="translate({cx:.1f},{cy:.1f}) scale({cell:.3f})">'
                   f'{inner}</g>')

    # actors
    for a in panel.get("actors", []):
        char = lib.get(a["char"])
        selection = {s: a[s] for s in char.slots if s in a}
        out.append(char.place(
            selection,
            cx=ax(a.get("x", 0.5)),
            cy=ay(a.get("y", 0.6)),
            height=a.get("scale", 0.8) * ph,
            flip=a.get("flip", False),
        ))

    # bubbles (on top)
    for b in panel.get("bubbles", []):
        to = b.get("to")
        tail = (ax(to[0]), ay(to[1])) if to else None
        out.append(bubble(
            b["text"], ax(b.get("x", 0.5)), ay(b.get("y", 0.18)),
            tail=tail, kind=b.get("kind", "speech"),
            max_chars=b.get("max_chars", 22), fs=b.get("fs", 16),
        ))

    out.append("</g>")
    # crisp panel border on top of clipped content
    out.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
               f'rx="10" fill="none" stroke="{INK}" stroke-width="3.5"/>')
    return "\n".join(out)


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def render_spec(spec, out_path: str | Path, library=None):
    """Render to .svg, .png, or .pdf based on extension. Returns the SVG string."""
    if not isinstance(spec, dict):
        spec = load_spec(spec)
    svg = build_svg(spec, library)
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
