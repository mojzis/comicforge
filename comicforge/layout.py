"""Bubble layout: where each bubble of a panel goes and where its tail points.

Pure geometry — nothing here draws. ``render`` turns the placements into SVG;
``validate`` reads them for layout warnings; ``render.bubble_layout`` hands
them to an editor that wants to draw handles.

All coordinates are page px inside the art box ``(px, py, pw, ph)``; panel
fractions in the spec are relative to that box.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import pairwise

from .bubbles import (
    ANCHORS,
    Tail,
    body_size,
    bubble_size,
    merge_style,
    resolve_style,
    tail_geometry,
    tail_look,
)

# How far from a panel edge a bubble is kept, and the gap left between two
# bubbles that stack because neither declared a `y`.
BUBBLE_INSET = 8.0
BUBBLE_GAP = 10.0
# In reading order a later bubble's top sits at least this share of the
# previous bubble's height lower, so the order reads at a glance.
READING_DROP = 0.5
# Tops closer than this share of the earlier bubble's height count as level,
# and level bubbles read left to right.
LEVEL = 0.25
# Reading-order placement keeps a bubble at least this share of the panel's
# shorter side away from every speaker point.
SPEAKER_CLEARANCE = 0.08

# a curve or line tail with no `tail_bend` bows this much, away from the
# nearest other bubble (or the panel centre) so neighbouring tails part
AUTO_BEND = 0.35

# a warning quotes this much of a bubble's text
LABEL_CHARS = 24

# per-bubble keys that override the page's `bubble_style` for that bubble
_TAIL_KEYS = ("tail", "tail_gap", "tail_from", "tail_bend")


@dataclass(frozen=True)
class Placement:
    """One laid-out bubble: its outer box and, if it has one, its tail."""

    index: int
    text: str  # as drawn (after `uppercase`)
    kind: str
    max_chars: int
    fs: float
    style: dict  # resolved: page `bubble_style` + the bubble's own tail keys
    centre: tuple[float, float]
    size: tuple[float, float]  # outer width, height (tail excluded)
    speaker: str | None
    auto: bool  # placed in reading order (no x / y / at)
    tail: Tail | None

    @property
    def box(self) -> tuple[float, float, float, float]:
        (bx, by), (bw, bh) = self.centre, self.size
        return bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2


def head(actor: dict) -> tuple[float, float]:
    """An actor's head in panel fractions, from its x / y / scale."""
    return (
        actor.get("x", 0.5),
        max(actor.get("y", 0.6) - actor.get("scale", 0.8) * 0.42, 0.05),
    )


def speaker_points(panel: dict) -> dict[str, tuple[float, float]]:
    """Every name a bubble's `speaker:` can resolve to, in panel fractions: the
    panel's `speakers:` points, overridden by the head of the first actor of
    that `char` (actors win)."""
    points = {
        name: (float(xy[0]), float(xy[1]))
        for name, xy in (panel.get("speakers") or {}).items()
    }
    actors: dict[str, dict] = {}
    for a in panel.get("actors", []):
        actors.setdefault(a["char"], a)
    points.update({char: head(a) for char, a in actors.items()})
    return points


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
def _anchor(at):
    if at is None:
        return "c", "t"
    if at not in ANCHORS:
        raise ValueError(f"unknown bubble anchor {at!r}; use one of {sorted(ANCHORS)}")
    return ANCHORS[at]


def _stack(edge, bx, bw, bh, placed, py, ph, start=None):
    """Vertical centre for a bubble of width *bw* / height *bh* centred on
    *bx*: `t` sits as high as it can (but no higher than *start*), `b` as low
    as it can, moving past any bubble already *placed* (list of (x0, y0, x1,
    y1) boxes) that it would overlap; `c` sits in the middle of the panel."""
    if edge == "c":
        return py + ph / 2
    x0, x1 = bx - bw / 2, bx + bw / 2
    if edge == "b":
        top = py + ph - BUBBLE_INSET - bh
    else:
        top = py + BUBBLE_INSET if start is None else start
    moved = True
    while moved:
        moved = False
        for bx0, by0, bx1, by1 in placed:
            if bx0 < x1 and bx1 > x0 and by0 < top + bh and by1 > top:
                top = by0 - BUBBLE_GAP - bh if edge == "b" else by1 + BUBBLE_GAP
                moved = True
    return top + bh / 2


def _covers(box, point) -> bool:
    x0, y0, x1, y1 = box
    return x0 < point[0] < x1 and y0 < point[1] < y1


def _crosses(a0, a1, b0, b1) -> bool:
    """Whether segments a0-a1 and b0-b1 properly intersect."""

    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    d1, d2 = side(b0, b1, a0), side(b0, b1, a1)
    d3, d4 = side(a0, a1, b0), side(a0, a1, b1)
    return d1 * d2 < 0 and d3 * d4 < 0


def _aim(tail: Tail):
    """The segment a reader's eye follows: from the bubble to its target."""
    return tail.start, tail.target


def _reading_spot(bw, bh, body, point, target, prev, placed, tails, points, box, st):
    """Centre for a bubble placed in reading order.

    Tries a few spots on the speaker's side — over the speaker, hugging that
    side's edge, just clear of the head either way, and each of those again
    below the head — every one at least ``READING_DROP`` below the previous
    bubble's top and past any bubble it would overlap, and keeps the one that
    covers no speaker, crosses no earlier tail, keeps the order, and stays
    closest to its speaker and highest up.
    """
    px, py, pw, ph = box
    body_w, body_h = body
    sx, sy = px + point[0] * pw, py + point[1] * ph
    mid = px + pw / 2
    right = sx >= mid
    hug = px + pw - BUBBLE_INSET - bw / 2 if right else px + BUBBLE_INSET + bw / 2
    start = py + BUBBLE_INSET
    if prev is not None:
        start = max(start, prev.box[1] + prev.size[1] * READING_DROP)
    # a point is a head's centre, not its extent: keep this far off it
    clear = max(2 * BUBBLE_GAP, SPEAKER_CLEARANCE * min(pw, ph))
    off = clear + 1  # just past the clearance, so these spots count as clear
    xs = [sx, hug, sx - bw / 2 - off, sx + bw / 2 + off]
    starts = [start, max(start, sy + off)]

    def score(bx, by):
        x0, top, x1, y1 = bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2
        grown = (x0 - clear, top - clear, x1 + clear, y1 + clear)
        s = 10.0 * sum(_covers(grown, p) for p in points)
        if target is not None:
            aim = _aim(tail_geometry(bx, by, body_w, body_h, target, st))
            s += 5.0 * sum(_crosses(*aim, *_aim(t)) for t in tails)
        if top < start - 0.5:  # clamped back up past the previous bubble
            s += 20.0
        s += (max(0.0, mid - x0) if right else max(0.0, x1 - mid)) / pw
        s += 0.5 * abs(bx - sx) / pw
        s += 0.3 * (top - start) / ph
        return s

    spots = []
    for top in starts:
        for x in xs:
            bx = _clamp(x, bw, px, pw)
            by = _clamp(_stack("t", bx, bw, bh, placed, py, ph, top), bh, py, ph)
            spots.append((score(bx, by), len(spots), bx, by))
    _s, _i, bx, by = min(spots)
    return bx, by


def layout_bubbles(panel, px, py, pw, ph, bubble_style=None) -> list[Placement]:
    """Place a panel's bubbles in the art box ``(px, py, pw, ph)``.

    Precedence per bubble: explicit ``x`` / ``y``, then ``at``, then its
    ``speaker``, then centred and stacked from the top. On a panel with
    ``speakers:`` a bubble with a speaker and none of ``x`` / ``y`` / ``at`` is
    placed in reading order instead (see :func:`_reading_spot`). Every bubble
    is finally kept inside the box.
    """
    points = speaker_points(panel)
    reading = bool(panel.get("speakers"))
    page_style = resolve_style(bubble_style)
    box = (px, py, pw, ph)
    heads = [(px + fx * pw, py + fy * ph) for fx, fy in points.values()]

    out: list[Placement] = []
    placed = []  # (x0, y0, x1, y1) of every bubble so far, for stacking
    for i, b in enumerate(panel.get("bubbles", [])):
        speaker = b.get("speaker")
        point = points.get(speaker) if speaker else None
        to = b.get("to") or point
        target = (px + to[0] * pw, py + to[1] * ph) if to else None
        text = b["text"]
        if b.get("uppercase", page_style["uppercase"]):
            text = text.upper()
        kind = b.get("kind", "speech")
        max_chars = b.get("max_chars", 22)
        fs = b.get("fs", page_style["font_size"])
        st = merge_style(page_style, {k: b.get(k) for k in _TAIL_KEYS})
        if tail_look(st)[0] == "none":
            target = None
        bw, bh = bubble_size(text, kind, max_chars, fs, style=st)
        body_w, body_h = body = body_size(text, max_chars, fs, style=st)
        tails = [p.tail for p in out if p.tail is not None]
        auto = (
            reading
            and point is not None
            and all(b.get(k) is None for k in ("x", "y", "at"))
        )
        if auto:
            prev = out[-1] if out else None
            bx, by = _reading_spot(
                bw, bh, body, point, target, prev, placed, tails, heads, box, st
            )
        else:
            col, edge = _anchor(b.get("at"))
            if b.get("x") is not None:
                bx = px + b["x"] * pw
            elif col == "c":
                bx = px + (point[0] if point else 0.5) * pw
            elif col == "l":
                bx = px + BUBBLE_INSET + bw / 2
            else:
                bx = px + pw - BUBBLE_INSET - bw / 2
            bx = _clamp(bx, bw, px, pw)
            if b.get("y") is not None:
                by = py + b["y"] * ph
            else:
                by = _stack(edge, bx, bw, bh, placed, py, ph)
            by = _clamp(by, bh, py, ph)
        tail = tail_geometry(bx, by, body_w, body_h, target, st) if target else None
        p = Placement(
            i, text, kind, max_chars, fs, st, (bx, by), (bw, bh), speaker, auto, tail
        )
        placed.append(p.box)
        out.append(p)
    return [_auto_bend(p, out, box) for p in out]


def _auto_bend(p: Placement, placements: list[Placement], box) -> Placement:
    """*p* with its curve / line tail bowed ``AUTO_BEND`` away from the nearest
    other bubble — or, alone in the panel, from the panel centre — unless it
    sets ``tail_bend`` itself. The chosen bend goes into its style, so drawing
    the bubble from that style reproduces the same tail."""
    tail = p.tail
    if tail is None or tail.shape not in ("curve", "line"):
        return p
    if p.style.get("tail_bend") is not None:
        return p
    others = [o.centre for o in placements if o is not p]
    px, py, pw, ph = box
    (sx, sy), (tx, ty) = tail.start, tail.target
    if others:
        ax, ay = min(others, key=lambda c: (c[0] - sx) ** 2 + (c[1] - sy) ** 2)
    else:
        ax, ay = px + pw / 2, py + ph / 2
    # which side of the tail's line the thing to avoid is on: + is the side a
    # positive bend bows toward
    side = (tx - sx) * (ay - sy) - (ty - sy) * (ax - sx)
    st = {**p.style, "tail_bend": -AUTO_BEND if side > 0 else AUTO_BEND}
    body_w, body_h = body_size(p.text, p.max_chars, p.fs, style=st)
    new_tail = tail_geometry(*p.centre, body_w, body_h, tail.target, st)
    return replace(p, style=st, tail=new_tail)


def _label(p: Placement) -> str:
    text = p.text
    if len(text) > LABEL_CHARS:
        text = text[: LABEL_CHARS - 1] + "…"
    return f'bubble {p.index} "{text}"'


def layout_warnings(placements: list[Placement], points: dict) -> list[str]:
    """Readability problems in a laid-out panel: a bubble that reads out of
    order (its top above the previous bubble's, or level with it but further
    left), two tails whose lines cross, a bubble covering a speaker point.
    *points* maps speaker name -> page px."""
    out = []
    for prev, cur in pairwise(placements):
        drop = cur.box[1] - prev.box[1]
        level = LEVEL * prev.size[1]
        if drop <= -level:
            out.append(
                f"{_label(cur)} sits above {_label(prev)} but comes after it "
                "(out of reading order)"
            )
        elif abs(drop) < level and cur.centre[0] < prev.centre[0]:
            out.append(
                f"{_label(cur)} is level with {_label(prev)} but left of it "
                "(out of reading order)"
            )
    tailed = [p for p in placements if p.tail is not None]
    for i, a in enumerate(tailed):
        out.extend(
            f"tails of {_label(a)} and {_label(b)} cross"
            for b in tailed[i + 1 :]
            if _crosses(*_aim(a.tail), *_aim(b.tail))  # ty: ignore[invalid-argument-type]
        )
    for p in placements:
        out.extend(
            f"{_label(p)} covers speaker '{name}'"
            for name, xy in points.items()
            if _covers(p.box, xy)
        )
    return out
