"""Narration captions: a text band inside the panel frame, under the art.

A panel's ``caption:`` is the narrator's voice ("Rain came. Snow came.") as
opposed to a bubble, which is a character's. It is drawn as a flat band along
the bottom of the panel, separated from the art by a hairline; the art box
shrinks to make room, so bubbles and actors keep their coordinates relative to
the picture, not the band. A page's ``caption_style:`` sets the look for every
caption; a panel can give ``caption: {text:, max_chars:}`` to wrap differently.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .bubbles import FONT, INK, _wrap

DEFAULT_STYLE = {
    "font": FONT,
    "font_size": 13,
    "ink": INK,  # text colour
    "bg": "#ffffff",  # band colour
    "pad": 8,  # text inset from the band edge
    "max_chars": 60,  # wrap width; a panel's caption can override
    "align": "left",  # left | center
    "rule": True,  # hairline between art and band (in the frame colour)
    "uppercase": False,
}


def normalize(value) -> dict | None:
    """``caption: text`` or ``caption: {text, max_chars}`` -> dict, or None."""
    if value is None:
        return None
    if isinstance(value, str):
        value = {"text": value}
    if not isinstance(value, dict) or not value.get("text"):
        raise ValueError("caption must be a string or a {text, max_chars} mapping")
    return value


def resolve_style(*layers) -> dict:
    out = dict(DEFAULT_STYLE)
    for layer in layers:
        if layer:
            out.update({k: v for k, v in layer.items() if v is not None})
    return out


def lines(caption: dict, style: dict) -> list[str]:
    text = " ".join(caption["text"].split())
    if caption.get("uppercase", style["uppercase"]):
        text = text.upper()
    return _wrap(text, caption.get("max_chars", style["max_chars"]))


def height(caption, style=None) -> float:
    """Band height in px a caption will take, 0 when there is none."""
    cap = normalize(caption)
    if cap is None:
        return 0.0
    st = resolve_style(style)
    return len(lines(cap, st)) * st["font_size"] * 1.25 + 2 * st["pad"]


def band(caption: dict, style: dict, x, y, w, h, rule_color, rule_width) -> str:
    """SVG for the band occupying the (x, y, w, h) box."""
    st = style
    fs, lh = st["font_size"], st["font_size"] * 1.25
    parts = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{st["bg"]}"/>'
    ]
    if st["rule"] and rule_width > 0:
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{rule_color}" stroke-width="{rule_width}"/>'
        )
    if st["align"] == "center":
        tx, anchor = x + w / 2, "middle"
    else:
        tx, anchor = x + st["pad"], "start"
    top = y + st["pad"] + fs
    spans = "".join(
        f'<tspan x="{tx:.1f}" y="{top + i * lh:.1f}">{escape(ln)}</tspan>'
        for i, ln in enumerate(lines(caption, st))
    )
    parts.append(
        f'<text text-anchor="{anchor}" font-family="{st["font"]}" font-size="{fs}" '
        f'fill="{st["ink"]}">{spans}</text>'
    )
    return "".join(parts)
