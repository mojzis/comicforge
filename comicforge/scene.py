"""Load the scene library and compose a scene background.

A scene is a directory mirroring a character:
    base.svg, <slot>-<variant>.svg, scene.yaml

It uses the same base + stackable-overlay model as characters (see
:mod:`comicforge.library`), but a scene is always a single body (no poses) and
instead of being placed at a height it is scaled to *cover* a panel (or the
whole canvas, for a standalone illustration).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .library import _inner


@dataclass
class Scene:
    """A background: a base body plus stackable overlay variants, one viewBox."""

    name: str
    label: str
    w: float
    h: float
    slots: dict[str, list[str]]
    defaults: dict[str, str]
    base: str
    variants: dict[str, str] = field(default_factory=dict)

    def compose_inner(self, selection: dict[str, str]) -> str:
        parts = [self.base]
        for slot in self.slots:  # manifest order = draw order
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


class SceneLibrary:
    """Loads scenes from ``<root>/<name>/`` lazily, caching parsed scenes."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._cache: dict[str, Scene] = {}

    def get(self, name: str) -> Scene:
        if name in self._cache:
            return self._cache[name]
        sdir = self.root / name
        if not sdir.is_dir():
            avail = (
                [p.name for p in self.root.iterdir() if p.is_dir()]
                if self.root.is_dir()
                else []
            )
            raise KeyError(f"scene '{name}' not found in {self.root}. Have: {avail}")
        man = yaml.safe_load((sdir / "scene.yaml").read_text(encoding="utf-8"))
        w, h = man["viewbox"]
        slots = man.get("slots", {})
        variants = {}
        for slot, names in slots.items():
            for v in names:
                variants[f"{slot}-{v}"] = _inner(sdir / f"{slot}-{v}.svg")
        scene = Scene(
            name=man["name"],
            label=man.get("label", man["name"]),
            w=w,
            h=h,
            slots=slots,
            defaults=man.get("default", {}),
            base=_inner(sdir / "base.svg"),
            variants=variants,
        )
        self._cache[name] = scene
        return scene

    def manifest(self) -> dict:
        """Machine-readable contract: every scene, its slots and variants."""
        out = {}
        if not self.root.is_dir():
            return out
        for p in sorted(self.root.iterdir()):
            if p.is_dir() and (p / "scene.yaml").exists():
                c = self.get(p.name)
                out[c.name] = {
                    "label": c.label,
                    "slots": c.slots,
                    "default": c.defaults,
                }
        return out


def cover(scene: Scene, selection, px, py, pw, ph) -> str:
    """Place a scene so it fully covers the (px, py, pw, ph) box, centred."""
    s = max(pw / scene.w, ph / scene.h)
    ox = px + (pw - scene.w * s) / 2
    oy = py + (ph - scene.h * s) / 2
    return (
        f'<g transform="translate({ox:.2f},{oy:.2f}) scale({s:.4f})">\n'
        f"{scene.compose_inner(selection)}\n</g>"
    )
