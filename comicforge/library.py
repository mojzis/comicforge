"""Load the character library and compose a posed character.

A character is an **identity** (name, label, …) that owns one or more **poses**.
A pose is a body drawn in its own local viewBox; expressions ("face", …) are
*shared* overlays authored once and re-registered onto each pose.

Two on-disk shapes, both loaded here:

*Flat (single pose):* the classic layout — everything in one viewBox::

    <name>/
      base.svg                 the body
      <slot>-<variant>.svg     stackable overlays in the SAME viewBox
      character.yaml           name, label, viewbox, slots, default

*Posed (multiple poses):* the body changes between poses (sit vs walk), so each
pose gets its own ``base.svg``; the shared overlays live at the character root
and are translated onto each pose by an *anchor* (a reference point — e.g. the
head centre — that the overlays are drawn around)::

    <name>/
      character.yaml           name, label, anchor, slots (SHARED), default, poses
      <slot>-<variant>.svg     SHARED overlays, drawn around the canonical anchor
      poses/
        <pose>/
          pose.yaml            viewbox, anchor, slots (pose-specific), default
          base.svg             this pose's body
          <slot>-<variant>.svg pose-specific overlays (optional)

Composition = pose base + pose-specific overlays + shared overlays (each shifted
by ``pose.anchor - character.anchor``), stacked in the pose's local viewBox, then
wrapped in a ``<g transform>`` that places and scales it inside a panel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_SVG_INNER = re.compile(r"<svg[^>]*>(.*)</svg>", re.DOTALL)


def _inner(svg_path: Path) -> str:
    text = svg_path.read_text(encoding="utf-8")
    m = _SVG_INNER.search(text)
    if not m:
        raise ValueError(f"{svg_path} is not a well-formed <svg>…</svg> file")
    return m.group(1).strip()


def _load_variants(dir_: Path, slots: dict[str, list[str]]) -> dict[str, str]:
    """Read every ``<slot>-<variant>.svg`` overlay in *dir_* into inner markup."""
    out: dict[str, str] = {}
    for slot, names in slots.items():
        for v in names:
            out[f"{slot}-{v}"] = _inner(dir_ / f"{slot}-{v}.svg")
    return out


@dataclass
class Pose:
    """One body of a character, drawn in its own local viewBox."""

    name: str
    w: float
    h: float
    anchor: tuple[float, float]  # where shared overlays land in this pose
    base: str  # inner svg markup
    slots: dict[str, list[str]] = field(default_factory=dict)  # pose-specific
    defaults: dict[str, str] = field(default_factory=dict)
    variants: dict[str, str] = field(default_factory=dict)  # "slot-variant"


@dataclass
class Character:
    name: str
    label: str
    anchor: tuple[float, float]  # canonical point shared overlays draw around
    slots: dict[str, list[str]]  # SHARED slots (re-anchored onto each pose)
    defaults: dict[str, str]  # shared defaults (may include "pose")
    variants: dict[str, str]  # shared "slot-variant" -> inner
    poses: dict[str, Pose]
    default_pose: str

    def resolve_pose(self, pose: str | None) -> Pose:
        name = pose or self.default_pose
        if name not in self.poses:
            raise ValueError(
                f"{self.name}: no pose '{name}'. Available: {list(self.poses)}"
            )
        return self.poses[name]

    def slots_for(self, pose: str | None = None) -> dict[str, list[str]]:
        """Every selectable slot for a pose: shared slots + that pose's own slots."""
        return {**self.slots, **self.resolve_pose(pose).slots}

    def compose_inner(self, selection: dict[str, str], pose: str | None = None) -> str:
        """Inner SVG for this character in the chosen pose with the chosen variants."""
        p = self.resolve_pose(pose)
        parts = [p.base]

        # pose-specific overlays: drawn directly in the pose's own coordinates
        for slot in p.slots:  # manifest order = draw order
            variant = selection.get(slot, p.defaults.get(slot))
            if variant is None:
                continue
            if variant not in p.slots[slot]:
                raise ValueError(
                    f"{self.name}/{p.name}: slot '{slot}' has no variant "
                    f"'{variant}'. Available: {p.slots[slot]}"
                )
            parts.append(p.variants[f"{slot}-{variant}"])

        # shared overlays: authored around the canonical anchor, shifted onto this pose
        dx, dy = p.anchor[0] - self.anchor[0], p.anchor[1] - self.anchor[1]
        for slot in self.slots:
            variant = selection.get(
                slot, p.defaults.get(slot) or self.defaults.get(slot)
            )
            if variant is None:
                continue
            if variant not in self.slots[slot]:
                raise ValueError(
                    f"{self.name}: shared slot '{slot}' has no variant '{variant}'. "
                    f"Available: {self.slots[slot]}"
                )
            inner = self.variants[f"{slot}-{variant}"]
            if dx or dy:
                inner = f'<g transform="translate({dx:.2f},{dy:.2f})">\n{inner}\n</g>'
            parts.append(inner)
        return "\n".join(parts)

    def place(self, selection, cx, cy, height, flip=False, pose=None) -> str:
        """Place the character centred at (cx, cy) scaled so it is `height` tall."""
        p = self.resolve_pose(pose)
        s = height / p.h
        w, h = p.w * s, p.h * s
        tx, ty = cx - w / 2, cy - h / 2
        if flip:
            transform = f"translate({tx + w:.2f},{ty:.2f}) scale({-s:.4f},{s:.4f})"
        else:
            transform = f"translate({tx:.2f},{ty:.2f}) scale({s:.4f})"
        inner = self.compose_inner(selection, pose)
        return f'<g transform="{transform}">\n{inner}\n</g>'


def _load_character(cdir: Path) -> Character:
    man = yaml.safe_load((cdir / "character.yaml").read_text(encoding="utf-8"))
    name = man["name"]
    label = man.get("label", name)
    anchor = tuple(man.get("anchor", (0.0, 0.0)))
    shared_slots = man.get("slots", {})
    shared_defaults = man.get("default", {})
    shared_variants = _load_variants(cdir, shared_slots)

    poses: dict[str, Pose] = {}
    if "poses" in man:
        for pname in man["poses"]:
            pdir = cdir / "poses" / pname
            pman = yaml.safe_load((pdir / "pose.yaml").read_text(encoding="utf-8"))
            pw, ph = pman["viewbox"]
            pslots = pman.get("slots", {})
            poses[pname] = Pose(
                name=pname,
                w=pw,
                h=ph,
                anchor=tuple(pman.get("anchor", anchor)),
                base=_inner(pdir / "base.svg"),
                slots=pslots,
                defaults=pman.get("default", {}),
                variants=_load_variants(pdir, pslots),
            )
        default_pose = shared_defaults.get("pose") or man["poses"][0]
    else:
        # flat single-pose character: the body + overlays live at the root, in one
        # viewBox. The shared overlays sit at the canonical anchor (translate 0).
        w, h = man["viewbox"]
        poses["default"] = Pose(
            name="default", w=w, h=h, anchor=anchor, base=_inner(cdir / "base.svg")
        )
        default_pose = "default"

    return Character(
        name=name,
        label=label,
        anchor=anchor,
        slots=shared_slots,
        defaults=shared_defaults,
        variants=shared_variants,
        poses=poses,
        default_pose=default_pose,
    )


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
            raise KeyError(
                f"character '{name}' not found in {self.root}. Have: {avail}"
            )
        char = _load_character(cdir)
        self._cache[name] = char
        return char

    def manifest(self) -> dict:
        """Machine-readable contract: every character, its poses, slots and variants."""
        out = {}
        for p in sorted(self.root.iterdir()):
            if p.is_dir() and (p / "character.yaml").exists():
                c = self.get(p.name)
                entry: dict[str, object] = {
                    "label": c.label,
                    "slots": c.slots,  # shared across poses
                    "default": c.defaults,
                }
                # only advertise poses for genuinely multi-pose characters
                if list(c.poses) != ["default"]:
                    entry["default_pose"] = c.default_pose
                    entry["poses"] = {
                        name: {"slots": pose.slots, "default": pose.defaults}
                        for name, pose in c.poses.items()
                    }
                out[c.name] = entry
        return out
