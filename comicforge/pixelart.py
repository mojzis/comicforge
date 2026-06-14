"""Tiny pixel-art helper.

A sprite is a list of equal-length strings + a palette {char: color}.
'.' (or space) = transparent. Returns inner SVG in local coords (cols x rows),
placed into a panel the same way characters are.

Sprites are loaded from a directory of YAML files via :class:`PixelLibrary`.
Each ``<name>.yaml`` contains ``grid`` (list of strings) and ``palette``
(dict of char -> color).  Inline ``{grid, palette}`` specs also work with no
library.
"""

from __future__ import annotations

from pathlib import Path

import yaml


class PixelLibrary:
    """Loads pixel-art sprites from ``<root>/<name>.yaml`` lazily, caching."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._cache: dict[str, dict] = {}

    def get(self, name: str) -> dict:
        if name in self._cache:
            return self._cache[name]
        path = self.root / f"{name}.yaml"
        if not path.exists():
            avail = sorted(p.stem for p in self.root.glob("*.yaml"))
            raise KeyError(
                f"pixel art '{name}' not found in {self.root}. Available: {avail}"
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self._cache[name] = data
        return data


def sprite_svg(grid: list[str], palette: dict[str, str], cell: float = 1.0) -> str:
    rects = []
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch in (".", " "):
                continue
            color = palette.get(ch, "#000000")
            rects.append(
                f'<rect x="{c * cell:.2f}" y="{r * cell:.2f}" '
                f'width="{cell:.2f}" height="{cell:.2f}" fill="{color}"/>'
            )
    return f'<g shape-rendering="crispEdges">{"".join(rects)}</g>'


def dims(grid: list[str]) -> tuple[int, int]:
    return (max(len(r) for r in grid), len(grid))


def resolve(
    spec: dict,
    pixel_library: PixelLibrary | None = None,
) -> tuple[str, int, int]:
    """spec: {art: <library name>} OR {grid: [...], palette: {...}}.

    When ``spec`` has ``"art"``, a ``pixel_library`` must be provided.
    Inline ``{grid, palette}`` works with no library.
    Returns (inner_svg, cols, rows).
    """
    if "art" in spec:
        if pixel_library is None:
            raise ValueError(
                f"pixel art '{spec['art']}' requires a pixel library "
                "(pass pixel_library= or set pixel_dir: in the spec)"
            )
        b = pixel_library.get(spec["art"])
        grid, palette = b["grid"], b["palette"]
    else:
        grid, palette = spec["grid"], spec.get("palette", {})
    cols, rows = dims(grid)
    return sprite_svg(grid, palette), cols, rows
