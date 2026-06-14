"""Tiny pixel-art helper.

A sprite is a list of equal-length strings + a palette {char: color}.
'.' (or space) = transparent. Returns inner SVG in local coords (cols x rows),
placed into a panel the same way characters are.
"""
from __future__ import annotations

BUILTINS: dict[str, dict] = {
    "heart": {
        "palette": {"R": "#e8556d", "r": "#b83e54"},
        "grid": [
            ".RR..RR.",
            "RRRRRRRR",
            "RRRRRRRR",
            "RRRRRRRR",
            ".RRRRRR.",
            "..RRRR..",
            "...RR...",
        ],
    },
    "sun": {
        "palette": {"Y": "#f4c430", "o": "#e8923a"},
        "grid": [
            "...Y.Y...",
            "Y..YYY..Y",
            ".YoYYYoY.",
            "..YYYYY..",
            "YYYYYYYYY",
            "..YYYYY..",
            ".YoYYYoY.",
            "Y..YYY..Y",
            "...Y.Y...",
        ],
    },
    "star": {
        "palette": {"Y": "#f4c430"},
        "grid": [
            "....Y....",
            "....Y....",
            "...YYY...",
            "YYYYYYYYY",
            ".YYYYYYY.",
            "..YYYYY..",
            ".YYY.YYY.",
            ".YY...YY.",
        ],
    },
    "bone": {
        "palette": {"W": "#f3efe4", "g": "#cfc8b6"},
        "grid": [
            "WW.....WW",
            "WWW...WWW",
            ".WWWWWWW.",
            ".WWWWWWW.",
            "WWW...WWW",
            "WW.....WW",
        ],
    },
}


def sprite_svg(grid: list[str], palette: dict[str, str], cell: float = 1.0) -> str:
    rects = []
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch in (".", " "):
                continue
            color = palette.get(ch, "#000000")
            rects.append(
                f'<rect x="{c*cell:.2f}" y="{r*cell:.2f}" '
                f'width="{cell:.2f}" height="{cell:.2f}" fill="{color}"/>'
            )
    return f'<g shape-rendering="crispEdges">{"".join(rects)}</g>'


def dims(grid: list[str]) -> tuple[int, int]:
    return (max(len(r) for r in grid), len(grid))


def resolve(spec: dict) -> tuple[str, int, int]:
    """spec: {art: <builtin name>} OR {grid: [...], palette: {...}}.
    Returns (inner_svg, cols, rows)."""
    if "art" in spec:
        if spec["art"] not in BUILTINS:
            raise KeyError(f"unknown pixel art '{spec['art']}'. "
                           f"Built-ins: {sorted(BUILTINS)}")
        b = BUILTINS[spec["art"]]
        grid, palette = b["grid"], b["palette"]
    else:
        grid, palette = spec["grid"], spec.get("palette", {})
    cols, rows = dims(grid)
    return sprite_svg(grid, palette), cols, rows
