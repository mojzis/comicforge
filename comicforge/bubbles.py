"""Speech bubbles: speech, thought, and shout, with naive word-wrap + tails.

All coordinates here are absolute page px. A bubble is positioned by its centre
(bx, by); the tail points toward `tail` (also page px).
"""
from __future__ import annotations
import math
from xml.sax.saxutils import escape

FONT = "DejaVu Sans, Helvetica, Arial, sans-serif"
INK = "#21304a"


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


def _text_block(lines, cx, top, fs, lh):
    spans = []
    for i, ln in enumerate(lines):
        spans.append(
            f'<tspan x="{cx:.1f}" y="{top + fs + i * lh:.1f}">{escape(ln)}</tspan>'
        )
    weight = ""
    return (
        f'<text text-anchor="middle" font-family="{FONT}" '
        f'font-size="{fs}" fill="{INK}" {weight}>{"".join(spans)}</text>'
    )


def bubble(text, bx, by, tail=None, kind="speech", max_chars=22,
           fs=16, pad=14):
    lines = _wrap(text, max_chars)
    lh = fs * 1.25
    longest = max((len(l) for l in lines), default=1)
    w = max(longest * fs * 0.56 + 2 * pad, 60)
    h = len(lines) * lh + 2 * pad
    x, y = bx - w / 2, by - h / 2
    txt = _text_block(lines, bx, y + pad, fs, lh)

    if kind == "shout":
        body = _burst(x, y, w, h)
    elif kind == "thought":
        rx, ry = w / 2 + 6, h / 2 + 8
        body = (f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
                f'fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
    else:
        body = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                f'rx="{min(18, h/2):.1f}" fill="#ffffff" stroke="{INK}" '
                f'stroke-width="3"/>')

    tail_svg = ""
    if tail is not None:
        tail_svg = _tail(bx, by, w, h, tail, kind)

    return f'<g>{body}{tail_svg}{txt}</g>'


def _tail(bx, by, w, h, tail, kind):
    """A slim tail that drops from the bubble underside and points toward the
    target — but stops well short of it, so the tip never reaches the figure."""
    tx, ty = tail
    # exit from the bottom edge, nudged horizontally toward the target but kept
    # under the bubble body
    ex = min(max(tx, bx - w * 0.3), bx + w * 0.3)
    ey = by + h / 2
    dx, dy = tx - ex, ty - ey
    dist = math.hypot(dx, dy) or 1.0
    reach = min(dist * 0.45, 46)  # capped length keeps the tip off the figure
    ux, uy = dx / dist, dy / dist
    tipx, tipy = ex + ux * reach, ey + uy * reach

    if kind == "thought":
        dots = ""
        for f in (0.45, 0.74, 1.0):
            r = 6 * (1 - f) + 2.5
            dots += (f'<circle cx="{ex + ux * reach * f:.1f}" '
                     f'cy="{ey + uy * reach * f:.1f}" r="{r:.1f}" '
                     f'fill="#ffffff" stroke="{INK}" stroke-width="2.5"/>')
        return dots
    # narrow tapered tail for speech/shout
    perp = math.atan2(uy, ux) + math.pi / 2
    base = 6
    ax = ex + math.cos(perp) * base
    ay = ey + math.sin(perp) * base
    bx2 = ex - math.cos(perp) * base
    by2 = ey - math.sin(perp) * base
    return (f'<path d="M{ax:.1f} {ay:.1f} L{tipx:.1f} {tipy:.1f} L{bx2:.1f} {by2:.1f} Z" '
            f'fill="#ffffff" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>')


def _cloud(x, y, w, h):
    # rounded body + scalloped top edge via overlapping circles
    rx = min(20, h / 2)
    body = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx:.1f}" fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
    bumps = ""
    n = max(3, int(w // 34))
    for i in range(n):
        cx = x + (i + 0.5) * w / n
        bumps += (f'<circle cx="{cx:.1f}" cy="{y:.1f}" r="13" '
                  f'fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
    # mask the inner stroke segments by redrawing body fill on top edge
    cover = (f'<rect x="{x+3:.1f}" y="{y:.1f}" width="{w-6:.1f}" height="14" '
             f'fill="#ffffff" stroke="none"/>')
    return body + bumps + cover + body.replace('fill="#ffffff"', 'fill="none"')


def _burst(x, y, w, h):
    cx, cy = x + w / 2, y + h / 2
    rx, ry = w / 2 + 8, h / 2 + 8
    n = 18
    pts = []
    for i in range(n * 2):
        a = math.pi * i / n
        rr = 1.0 if i % 2 == 0 else 0.78
        pts.append(f"{cx + math.cos(a) * rx * rr:.1f},{cy + math.sin(a) * ry * rr:.1f}")
    return (f'<polygon points="{" ".join(pts)}" fill="#ffffff" '
            f'stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>')
