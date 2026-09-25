"""Narration captions: a text band inside the panel frame, under the art.

A panel's ``caption:`` is the narrator's voice ("Rain came. Snow came.") as
opposed to a bubble, which is a character's. It is drawn as a flat band along
the bottom of the panel, separated from the art by a hairline; the art box
shrinks to make room, so bubbles and actors keep their coordinates relative to
the picture, not the band. A page's ``caption_style:`` sets the look for every
caption; a panel can give ``caption: {text:, max_chars:}`` to wrap differently.

``max_chars: auto`` wraps to the band's width instead of a character count,
measuring the text with the bubble estimate scaled by the style's ``em`` — set
``em`` below 1 for a font narrower than DejaVu Sans.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .bubbles import FONT, INK, _wrap, chunks, merge_style, squeeze, text_width

DEFAULT_STYLE = {
    "font": FONT,
    "font_size": 13,
    "ink": INK,  # text colour
    "bg": "#ffffff",  # band colour
    "pad": 8,  # text inset from the band edge
    "max_chars": 60,  # wrap width; "auto" = the band's width; a caption can override
    "em": 1.0,  # width scale for the text measure when max_chars is auto
    "align": "left",  # left | center
    "rule": True,  # hairline between art and band (in the frame colour)
    "uppercase": False,
    "glue_singles": True,  # never end a line with a one-letter word, see `chunks`
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
    return merge_style(DEFAULT_STYLE, *layers)


def lines(caption: dict, style: dict, width: float | None = None) -> list[str]:
    """Wrap a caption for a band *width* px wide (needed for ``max_chars: auto``)."""
    text = squeeze(caption["text"])
    if caption.get("uppercase", style["uppercase"]):
        text = text.upper()
    glue = caption.get("glue_singles", style["glue_singles"])
    max_chars = caption.get("max_chars", style["max_chars"])
    if max_chars != "auto":
        return _wrap(text, max_chars, glue)
    if width is None:
        raise ValueError("caption max_chars: auto needs the band width to wrap to")
    return _wrap_to(
        text, width - 2 * style["pad"], style["font_size"] * style["em"], glue
    )


def _wrap_to(
    text: str, limit: float, fs: float, glue_singles: bool = True
) -> list[str]:
    """Greedy word wrap so no line measures wider than *limit* px (a single
    over-long word still gets a line of its own)."""
    out, cur = [], ""
    for word in chunks(text, glue_singles):
        trial = f"{cur} {word}" if cur else word
        if cur and text_width(trial, fs) > limit:
            out.append(cur)
            cur = word
        else:
            cur = trial
    return [*out, cur] if cur else out or [""]


def height(caption, style=None, width: float | None = None) -> float:
    """Band height in px a caption will take in a panel *width* px wide, 0 when
    there is none."""
    cap = normalize(caption)
    if cap is None:
        return 0.0
    st = resolve_style(style)
    return len(lines(cap, st, width)) * st["font_size"] * 1.25 + 2 * st["pad"]


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
        for i, ln in enumerate(lines(caption, st, w))
    )
    parts.append(
        f'<text text-anchor="{anchor}" font-family="{st["font"]}" font-size="{fs}" '
        f'fill="{st["ink"]}">{spans}</text>'
    )
    return "".join(parts)
