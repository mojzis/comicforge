"""Speech bubbles: speech, thought, and shout, with naive word-wrap + tails.

All coordinates here are absolute page px. A bubble is positioned by its centre
(bx, by); the tail points toward `tail` (also page px).
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

FONT = "DejaVu Sans, Helvetica, Arial, sans-serif"
INK = "#21304a"

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
}


def resolve_style(*layers) -> dict:
    """Merge style dicts over ``DEFAULT_STYLE``; later layers win, ``None`` skipped."""
    out = dict(DEFAULT_STYLE)
    for layer in layers:
        if layer:
            out.update({k: v for k, v in layer.items() if v is not None})
    return out


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

    tail_svg = ""
    if tail is not None:
        tail_svg = _tail(bx, by, w, h, tail, kind, st)

    return f"<g>{body}{tail_svg}{txt}</g>"


def _tail(bx, by, w, h, tail, kind, st):
    """A slim tail from the bubble's underside (or its top, when the speaker is
    above it) pointing toward the target — but stopping well short of it, so
    the tip never reaches the figure."""
    tx, ty = tail
    # exit from the edge facing the target: a side edge when the target lies
    # further out beside the bubble than above or below it (relative to the
    # body's own size), else top/bottom — nudged toward the target but kept
    # within the middle of that edge
    over_x = (abs(tx - bx) - w / 2) / (w / 2)
    over_y = (abs(ty - by) - h / 2) / (h / 2)
    if over_x > 0 and over_x > over_y:
        ex = bx - w / 2 if tx < bx else bx + w / 2
        ey = min(max(ty, by - h * 0.3), by + h * 0.3)
    else:
        ex = min(max(tx, bx - w * 0.3), bx + w * 0.3)
        ey = by - h / 2 if ty < by - h / 2 else by + h / 2
    dx, dy = tx - ex, ty - ey
    dist = math.hypot(dx, dy) or 1.0
    reach = min(dist * 0.45, 46)  # capped length keeps the tip off the figure
    ux, uy = dx / dist, dy / dist
    tipx, tipy = ex + ux * reach, ey + uy * reach

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
