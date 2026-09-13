"""Speech bubbles: speech, thought, and shout, with naive word-wrap + tails.

All coordinates here are absolute page px. A bubble is positioned by its centre
(bx, by); the tail points toward `tail` (also page px).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from xml.sax.saxutils import escape

FONT = "DejaVu Sans, Helvetica, Arial, sans-serif"
INK = "#21304a"

# `at:` anchor -> (horizontal, vertical) edge: l/c/r x t/c/b. Bubbles use it to
# hug a corner of the panel; a raster image uses it to pick which part survives
# a crop.
ANCHORS = {
    "tl": ("l", "t"), "t": ("c", "t"), "tc": ("c", "t"), "tr": ("r", "t"),
    "bl": ("l", "b"), "b": ("c", "b"), "bc": ("c", "b"), "br": ("r", "b"),
    "l": ("l", "c"), "c": ("c", "c"), "r": ("r", "c"), "cl": ("l", "c"),
    "cr": ("r", "c"),
}  # fmt: skip

# Every knob a bubble's look has. A page's `bubble_style:` overrides any of
# these for the whole page; a bubble's own keys override again.
DEFAULT_STYLE = {
    "font": FONT,
    "font_size": 16,
    "pad": 14,  # text inset from the outline
    "radius": 18,  # corner radius of a speech bubble (capped at half height)
    "stroke": INK,  # outline colour
    "stroke_width": 3,
    "fill": "#ffffff",
    "ink": INK,  # text colour
    "uppercase": False,
    "em": 1.0,  # width scale for the text measure: <1 for a narrower font
    "tail_shape": "wedge",  # wedge (a slim, short tail) | line (runs to the speaker)
    "tail_gap": 12,  # `line` only: px left between the line's end and its target
    "tail_from": None,  # where the tail leaves the bubble, see `tail_from`
}

TAIL_SHAPES = ("wedge", "line")
TAIL_EDGES = ("t", "b", "l", "r")


def merge_style(defaults: dict, *layers) -> dict:
    """Merge style dicts over *defaults*; later layers win, ``None`` values and
    empty layers are skipped."""
    out = dict(defaults)
    for layer in layers:
        if layer:
            out.update({k: v for k, v in layer.items() if v is not None})
    return out


def resolve_style(*layers) -> dict:
    """Merge style dicts over ``DEFAULT_STYLE``; later layers win, ``None`` skipped."""
    return merge_style(DEFAULT_STYLE, *layers)


def _wrap(text: str, max_chars: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


# Rough advance widths in em for a humanist sans (DejaVu Sans is the default
# font): capitals are a good third wider than lowercase, so an all-caps bubble
# must be measured as such or the text runs past its outline.
_EM = {"upper": 0.70, "lower": 0.56, "digit": 0.64, "space": 0.32, "other": 0.34}


def text_width(text: str, fs: float) -> float:
    """Estimated rendered width of *text* at font size *fs*, in px."""

    def em(ch):
        if ch.isupper():
            return _EM["upper"]
        if ch.islower():
            return _EM["lower"]
        if ch.isdigit():
            return _EM["digit"]
        if ch.isspace():
            return _EM["space"]
        return _EM["other"]

    return sum(em(ch) for ch in text) * fs


def _box(text, max_chars, fs, pad, em=1.0):
    """Wrap *text* and return (lines, line_height, body_width, body_height)."""
    lines = _wrap(text, max_chars)
    lh = fs * 1.25
    longest = max((text_width(ln, fs) * em for ln in lines), default=fs)
    w = max(longest + 2 * pad, 60)
    h = len(lines) * lh + 2 * pad
    return lines, lh, w, h


# how far each bubble kind's outline reaches beyond the text body box
_OUTSET = {"thought": (12, 16), "shout": (16, 16)}


def bubble_size(text, kind="speech", max_chars=22, fs=None, pad=None, style=None):
    """Outer (width, height) a `bubble` call will occupy, tail excluded.

    `thought` and `shout` draw outside the text body, so callers that stack
    bubbles or keep them inside a panel need this, not just the body box.
    """
    st = resolve_style(style)
    fs = st["font_size"] if fs is None else fs
    pad = st["pad"] if pad is None else pad
    _lines, _lh, w, h = _box(text, max_chars, fs, pad, st["em"])
    ow, oh = _OUTSET.get(kind, (0, 0))
    return w + ow, h + oh


def _text_block(lines, cx, top, fs, lh, st):
    spans = []
    for i, ln in enumerate(lines):
        spans.append(
            f'<tspan x="{cx:.1f}" y="{top + fs + i * lh:.1f}">{escape(ln)}</tspan>'
        )
    return (
        f'<text text-anchor="middle" font-family="{st["font"]}" '
        f'font-size="{fs}" fill="{st["ink"]}">{"".join(spans)}</text>'
    )


def _paint(st, scale=1.0):
    """fill/stroke attributes shared by every outline a bubble draws."""
    return (
        f'fill="{st["fill"]}" stroke="{st["stroke"]}" '
        f'stroke-width="{st["stroke_width"] * scale:.2f}"'
    )


def body_size(text, max_chars=22, fs=None, pad=None, style=None):
    """(width, height) of the text body a bubble's tail is measured against."""
    st = resolve_style(style)
    fs = st["font_size"] if fs is None else fs
    pad = st["pad"] if pad is None else pad
    _lines, _lh, w, h = _box(text, max_chars, fs, pad, st["em"])
    return w, h


def tail_from(value) -> tuple[str | None, float | None]:
    """Normalise a ``tail_from`` value to ``(edge, pos)``.

    ``b`` picks an edge (``t``/``b``/``l``/``r``) and lets the tail slide along
    it toward the target; ``0.3`` keeps the automatic edge and fixes the spot
    along it (0 = left / top end, 1 = right / bottom end); ``{edge: r, pos:
    0.4}`` fixes both. ``None`` is the automatic choice for both.
    """
    if value is None:
        return None, None
    if isinstance(value, str):
        edge, pos = value, None
    elif isinstance(value, dict):
        unknown = set(value) - {"edge", "pos"}
        if unknown:
            raise ValueError(
                f"unknown tail_from key(s) {sorted(unknown)}; use 'edge' and 'pos'"
            )
        edge, pos = value.get("edge"), value.get("pos")
    elif isinstance(value, int | float) and not isinstance(value, bool):
        edge, pos = None, value
    else:
        raise ValueError(  # noqa: TRY004 - a bad spec value, like every other
            f"tail_from must be an edge, a position 0..1 or {{edge, pos}}, "
            f"got {value!r}"
        )
    if edge is not None and edge not in TAIL_EDGES:
        raise ValueError(f"unknown tail edge {edge!r}; use one of {list(TAIL_EDGES)}")
    if pos is not None and (
        isinstance(pos, bool) or not isinstance(pos, int | float) or not 0 <= pos <= 1
    ):
        raise ValueError(f"tail_from pos must be a number from 0 to 1, got {pos!r}")
    return edge, pos


@dataclass(frozen=True)
class Tail:
    """Where a tail sits: it leaves the bubble's *edge* at *start* and is drawn
    toward *target*, ending at *tip*. All page px."""

    edge: str
    start: tuple[float, float]
    tip: tuple[float, float]
    target: tuple[float, float]
    shape: str = "wedge"


def tail_geometry(bx, by, w, h, target, style=None) -> Tail:
    """Geometry of the tail of a *w* x *h* body centred on (bx, by).

    By default it leaves the edge facing the target — a side edge when the
    target lies further out beside the bubble than above or below it (relative
    to the body's own size), else top/bottom — nudged toward the target but
    kept within the middle of that edge. ``tail_from`` in *style* pins the
    edge and/or the spot along it. A ``wedge`` stops well short of the target
    so the tip never reaches the figure; a ``line`` runs on to ``tail_gap`` px
    before it.
    """
    st = resolve_style(style)
    tx, ty = target
    edge, pos = tail_from(st["tail_from"])
    if edge is None:
        over_x = (abs(tx - bx) - w / 2) / (w / 2)
        over_y = (abs(ty - by) - h / 2) / (h / 2)
        if over_x > 0 and over_x > over_y:
            edge = "l" if tx < bx else "r"
        else:
            edge = "t" if ty < by - h / 2 else "b"
    if edge in ("l", "r"):
        ex = bx - w / 2 if edge == "l" else bx + w / 2
        if pos is None:
            ey = min(max(ty, by - h * 0.3), by + h * 0.3)
        else:
            ey = by - h / 2 + pos * h
    else:
        if pos is None:
            ex = min(max(tx, bx - w * 0.3), bx + w * 0.3)
        else:
            ex = bx - w / 2 + pos * w
        ey = by - h / 2 if edge == "t" else by + h / 2
    dx, dy = tx - ex, ty - ey
    dist = math.hypot(dx, dy) or 1.0
    shape = st["tail_shape"]
    # a wedge's capped length keeps the tip off the figure
    line = shape == "line"
    reach = max(dist - st["tail_gap"], 0.0) if line else min(dist * 0.45, 46)
    tip = (ex + dx / dist * reach, ey + dy / dist * reach)
    return Tail(edge, (ex, ey), tip, (tx, ty), shape)


def bubble(
    text, bx, by, tail=None, kind="speech", max_chars=22, fs=None, pad=None, style=None
):
    st = resolve_style(style)
    fs = st["font_size"] if fs is None else fs
    pad = st["pad"] if pad is None else pad
    lines, lh, w, h = _box(text, max_chars, fs, pad, st["em"])
    x, y = bx - w / 2, by - h / 2
    txt = _text_block(lines, bx, y + pad, fs, lh, st)

    if kind == "shout":
        body = _burst(x, y, w, h, st)
    elif kind == "thought":
        rx, ry = w / 2 + 6, h / 2 + 8
        body = (
            f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f"{_paint(st)}/>"
        )
    else:
        body = (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{min(st["radius"], h / 2):.1f}" {_paint(st)}/>'
        )

    under = tail_svg = ""
    if tail is not None:
        geom = tail_geometry(bx, by, w, h, tail, st)
        if geom.shape == "line":
            under, tail_svg = _line_tail(geom, kind, st)
        else:
            tail_svg = _tail(geom, kind, st)

    return f"<g>{under}{body}{tail_svg}{txt}</g>"


def _tail(geom: Tail, kind, st):
    """A slim tail from the bubble's edge toward the target, stopping short."""
    ex, ey = geom.start
    tipx, tipy = geom.tip
    reach = math.hypot(tipx - ex, tipy - ey) or 1.0
    ux, uy = (tipx - ex) / reach, (tipy - ey) / reach

    if kind == "thought":
        dots = ""
        for f in (0.45, 0.74, 1.0):
            r = 6 * (1 - f) + 2.5
            dots += (
                f'<circle cx="{ex + ux * reach * f:.1f}" '
                f'cy="{ey + uy * reach * f:.1f}" r="{r:.1f}" {_paint(st, 0.85)}/>'
            )
        return dots
    # narrow tapered tail for speech/shout
    perp = math.atan2(uy, ux) + math.pi / 2
    base = 6
    ax = ex + math.cos(perp) * base
    ay = ey + math.sin(perp) * base
    bx2 = ex - math.cos(perp) * base
    by2 = ey - math.sin(perp) * base
    return (
        f'<path d="M{ax:.1f} {ay:.1f} L{tipx:.1f} {tipy:.1f} '
        f'L{bx2:.1f} {by2:.1f} Z" {_paint(st, 0.85)} stroke-linejoin="round"/>'
    )


def _line_tail(geom: Tail, kind, st) -> tuple[str, str]:
    """(under, over) of a ``line`` tail: a thin ink line from the bubble to just
    short of the speaker, over a wider paper-coloured halo that keeps it legible
    on busy art — the halo goes under the bubble so it never eats the outline.
    A thought's line is a trail of small bubbles instead."""
    (ex, ey), (tipx, tipy) = geom.start, geom.tip
    sw = st["stroke_width"] * 0.8
    if kind == "thought":
        length = math.hypot(tipx - ex, tipy - ey)
        n = max(1, int(length // (sw * 4)))
        dots = "".join(
            f'<circle cx="{ex + (tipx - ex) * i / n:.1f}" '
            f'cy="{ey + (tipy - ey) * i / n:.1f}" r="{sw * 0.9:.2f}" '
            f"{_paint(st, 0.5)}/>"
            for i in range(1, n + 1)
        )
        return "", dots
    common = (
        f'd="M{ex:.1f} {ey:.1f} L{tipx:.1f} {tipy:.1f}" fill="none" '
        'stroke-linecap="round"'
    )
    halo = f'<path {common} stroke="{st["fill"]}" stroke-width="{sw * 2.2:.2f}"/>'
    line = f'<path {common} stroke="{st["stroke"]}" stroke-width="{sw:.2f}"/>'
    return halo, line


def _cloud(x, y, w, h):
    # rounded body + scalloped top edge via overlapping circles
    rx = min(20, h / 2)
    body = (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx:.1f}" fill="#ffffff" stroke="{INK}" stroke-width="3"/>'
    )
    bumps = ""
    n = max(3, int(w // 34))
    for i in range(n):
        cx = x + (i + 0.5) * w / n
        bumps += (
            f'<circle cx="{cx:.1f}" cy="{y:.1f}" r="13" '
            f'fill="#ffffff" stroke="{INK}" stroke-width="3"/>'
        )
    # mask the inner stroke segments by redrawing body fill on top edge
    cover = (
        f'<rect x="{x + 3:.1f}" y="{y:.1f}" width="{w - 6:.1f}" height="14" '
        f'fill="#ffffff" stroke="none"/>'
    )
    return body + bumps + cover + body.replace('fill="#ffffff"', 'fill="none"')


def _burst(x, y, w, h, st):
    cx, cy = x + w / 2, y + h / 2
    rx, ry = w / 2 + 8, h / 2 + 8
    n = 18
    pts = []
    for i in range(n * 2):
        a = math.pi * i / n
        rr = 1.0 if i % 2 == 0 else 0.78
        pts.append(f"{cx + math.cos(a) * rx * rr:.1f},{cy + math.sin(a) * ry * rr:.1f}")
    return f'<polygon points="{" ".join(pts)}" {_paint(st)} stroke-linejoin="round"/>'
