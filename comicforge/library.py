"""Load the character library and compose a posed character.

A character is a directory:
    base.svg, <slot>-<variant>.svg, character.yaml

Composition = base inner markup + chosen variant inner markup, stacked in the
character's shared local viewBox, then wrapped in a <g transform> that places
and scales it inside a panel.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml

_SVG_INNER = re.compile(r"<svg[^>]*>(.*)</svg>", re.S)


def _inner(svg_path: Path) -> str:
    text = svg_path.read_text(encoding="utf-8")
    m = _SVG_INNER.search(text)
    if not m:
        raise ValueError(f"{svg_path} is not a well-formed <svg>…</svg> file")
    return m.group(1).strip()


@dataclass
class Character:
    name: str
    label: str
    w: float
    h: float
    slots: dict[str, list[str]]
    defaults: dict[str, str]
    base: str                       # inner svg markup
    variants: dict[str, str] = field(default_factory=dict)  # "slot-variant" -> inner

    def compose_inner(self, selection: dict[str, str]) -> str:
        """Return inner SVG for this character with the chosen slot variants."""
        parts = [self.base]
        for slot in self.slots:                       # manifest order = draw order
            variant = selection.get(slot, self.defaults.get(slot))
            if variant is None:
                continue
            if variant not in self.slots[slot]:
                raise ValueError(
                    f"{self.name}: slot '{slot}' has no variant '{variant}'. "
                    f"Available: {self.slots[slot]}"
                )
            parts.append(self.variants[f"{slot}-{variant}"])
        return "\n".join(parts)

    def place(self, selection, cx, cy, height, flip=False) -> str:
        """Place the character centred at (cx, cy) scaled so it is `height` tall."""
        s = height / self.h
        w, h = self.w * s, self.h * s
        tx, ty = cx - w / 2, cy - h / 2
        if flip:
            transform = f"translate({tx + w:.2f},{ty:.2f}) scale({-s:.4f},{s:.4f})"
        else:
            transform = f"translate({tx:.2f},{ty:.2f}) scale({s:.4f})"
        return f'<g transform="{transform}">\n{self.compose_inner(selection)}\n</g>'


class Library:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._cache: dict[str, Character] = {}

    def get(self, name: str) -> Character:
        if name in self._cache:
            return self._cache[name]
        cdir = self.root / name
        if not cdir.is_dir():
            avail = [p.name for p in self.root.iterdir() if p.is_dir()]
            raise KeyError(f"character '{name}' not found in {self.root}. Have: {avail}")
        man = yaml.safe_load((cdir / "character.yaml").read_text(encoding="utf-8"))
        w, h = man["viewbox"]
        slots = man.get("slots", {})
        variants = {}
        for slot, names in slots.items():
            for v in names:
                variants[f"{slot}-{v}"] = _inner(cdir / f"{slot}-{v}.svg")
        char = Character(
            name=man["name"],
            label=man.get("label", man["name"]),
            w=w, h=h,
            slots=slots,
            defaults=man.get("default", {}),
            base=_inner(cdir / "base.svg"),
            variants=variants,
        )
        self._cache[name] = char
        return char

    def manifest(self) -> dict:
        """Machine-readable contract: every character, its slots and variants."""
        out = {}
        for p in sorted(self.root.iterdir()):
            if p.is_dir() and (p / "character.yaml").exists():
                c = self.get(p.name)
                out[c.name] = {
                    "label": c.label,
                    "slots": c.slots,
                    "default": c.defaults,
                }
        return out
