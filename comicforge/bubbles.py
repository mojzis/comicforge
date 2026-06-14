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
    tx, ty = tail
    ang = math.atan2(ty - by, tx - bx)
    # exit point on the bubble's bounding ellipse toward the target
    ex = bx + math.cos(ang) * (w / 2) * 0.82
    ey = by + math.sin(ang) * (h / 2) * 0.82
    if kind == "thought":
        dots = ""
        for f in (0.45, 0.72, 0.92):
            px = ex + (tx - ex) * f
            py = ey + (ty - ey) * f
            r = 7 * (1 - f) + 2
            dots += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
                     f'fill="#ffffff" stroke="{INK}" stroke-width="2.5"/>')
        return dots
    # solid triangle tail for speech/shout
    perp = ang + math.pi / 2
    spread = 11
    ax = ex + math.cos(perp) * spread
    ay = ey + math.sin(perp) * spread
    bx2 = ex - math.cos(perp) * spread
    by2 = ey - math.sin(perp) * spread
    return (f'<path d="M{ax:.1f} {ay:.1f} L{tx:.1f} {ty:.1f} L{bx2:.1f} {by2:.1f} Z" '
            f'fill="#ffffff" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>')


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
