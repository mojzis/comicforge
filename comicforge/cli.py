"""Command line interface.

python -m comicforge render examples/pes/pages/slepice.yaml -o out.pdf
python -m comicforge scene  examples/pes/pages/dvur-scene.yaml -o out.png
python -m comicforge characters --library examples/pes/characters
python -m comicforge scenes --scenes examples/pes/scenes
python -m comicforge inspire examples/pes/references.yaml --review

When `-o` is omitted, render/scene/panel/character write a timestamped file into
the gitignored ``output/`` dir (so successive renders accumulate for comparison).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from rich import print as rich_print

from .library import Library
from .pixelart import PixelLibrary
from .render import (
    render_all_panels,
    render_character,
    render_panel,
    render_scene,
    render_spec,
)
from .scene import SceneLibrary
from .validate import validate_spec

# Where renders land when -o is omitted. Gitignored; filenames carry a timestamp
# so successive renders accumulate and you can watch a page/character evolve.
OUTPUT_DIR = Path("output")


def _stamp() -> str:
    return datetime.now(UTC).astimezone().strftime("%Y%m%d-%H%M%S")


def _default_out(stem: str, ext: str = ".png") -> Path:
    """A timestamped path inside the gitignored output dir."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / f"{stem}-{_stamp()}{ext}"


def _parse_selection(char, tokens, pose):
    """Turn CLI tokens into a (selection, pose) pair for one character.

    A token is either ``key=value`` (``pose=walk``, ``face=happy``) or a bare
    name that is matched against the character's poses, then its slot variants.
    """
    # pass 1: settle the pose first, so variant lookup uses the right slots
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k == "pose":
                pose = v
        elif tok in char.poses:
            pose = tok

    slots = char.slots_for(pose)
    selection: dict[str, str] = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k != "pose":
                selection[k] = v
        elif tok in char.poses:
            continue
        else:
            slot = next((s for s, variants in slots.items() if tok in variants), None)
            if slot is None:
                raise SystemExit(
                    f"don't know '{tok}' for {char.name}: "
                    f"not a pose {list(char.poses)} nor a variant in {slots}"
                )
            selection[slot] = tok
    return selection, pose


def main(argv=None):  # noqa: PLR0912, PLR0915 — flat CLI dispatcher; clearer linear
    p = argparse.ArgumentParser(prog="comicforge")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser(
        "init", help="scaffold a new data-only project (no Python needed)"
    )
    init.add_argument(
        "dest", type=Path, help="directory to create the project in (e.g. ./my-comic)"
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files (default: skip files that already exist)",
    )

    r = sub.add_parser("render", help="render a comic page spec")
    r.add_argument("spec", type=Path)
    r.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="output .svg / .png / .pdf (default: output/<spec>-<timestamp>.png)",
    )
    r.add_argument("--library", type=Path, default=None)
    r.add_argument("--scenes", type=Path, default=None)
    r.add_argument(
        "--pixel-dir",
        type=Path,
        default=None,
        dest="pixel_dir",
        help="pixel-art sprite library directory",
    )

    v = sub.add_parser(
        "validate", help="check a page/scene spec against its libraries (no render)"
    )
    v.add_argument("spec", type=Path)
    v.add_argument("--library", type=Path, default=None)
    v.add_argument("--scenes", type=Path, default=None)
    v.add_argument(
        "--pixel-dir",
        type=Path,
        default=None,
        dest="pixel_dir",
        help="pixel-art sprite library directory",
    )

    s = sub.add_parser("scene", help="render a standalone scene illustration")
    s.add_argument("spec", type=Path)
    s.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="output .svg / .png / .pdf (default: output/<spec>-<timestamp>.png)",
    )
    s.add_argument("--library", type=Path, default=None)
    s.add_argument("--scenes", type=Path, default=None)
    s.add_argument(
        "--pixel-dir",
        type=Path,
        default=None,
        dest="pixel_dir",
        help="pixel-art sprite library directory",
    )

    pn = sub.add_parser(
        "panel", help="render individual panel(s) at low res for review"
    )
    pn.add_argument("spec", type=Path)
    pn.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="output file, or a directory when --all "
        "(default: timestamped path under output/)",
    )
    pn.add_argument("--row", type=int, default=0)
    pn.add_argument("--col", type=int, default=0)
    pn.add_argument(
        "--all", action="store_true", help="render every panel into the -o directory"
    )
    pn.add_argument(
        "--scale",
        type=float,
        default=0.5,
        help="size vs full-page panel (default 0.5 = low res)",
    )
    pn.add_argument("--library", type=Path, default=None)
    pn.add_argument("--scenes", type=Path, default=None)
    pn.add_argument(
        "--pixel-dir",
        type=Path,
        default=None,
        dest="pixel_dir",
        help="pixel-art sprite library directory",
    )

    ch = sub.add_parser(
        "character", help="render a single character on its own, for review"
    )
    ch.add_argument("name", help="character to render")
    ch.add_argument(
        "selections",
        nargs="*",
        help="pose and slot variants as bare names (sit, happy) or key=value "
        "(face=happy, pose=walk)",
    )
    ch.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="output .svg / .png / .pdf (default: output/<name>-<timestamp>.png)",
    )
    ch.add_argument(
        "--library", type=Path, required=True, help="character library directory"
    )
    ch.add_argument(
        "--pose", default=None, help="pose to render (default: character's)"
    )
    ch.add_argument(
        "--scale", type=float, default=2.0, help="px per viewBox unit (default 2)"
    )
    ch.add_argument("--bg", default="#ffffff", help="canvas background colour")
    ch.add_argument("--flip", action="store_true", help="mirror horizontally")
    ch.add_argument(
        "--thumb-px",
        type=int,
        default=320,
        dest="thumb_px",
        help="body width of the small companion PNG (0 to skip it)",
    )

    c = sub.add_parser("characters", help="print the character library contract")
    c.add_argument(
        "--library",
        type=Path,
        required=True,
        help="character library directory (required)",
    )

    sc = sub.add_parser("scenes", help="print the scene library contract")
    sc.add_argument(
        "--scenes", type=Path, required=True, help="scenes directory (required)"
    )

    ins = sub.add_parser(
        "inspire", help="generate reference images from a theme + descriptions"
    )
    ins.add_argument("references", type=Path, help="references spec (list of items)")
    ins.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="output dir (default: references/ next to the spec)",
    )
    ins.add_argument(
        "--theme",
        type=Path,
        default=None,
        help="theme.yaml (default: sibling of the spec)",
    )
    ins.add_argument(
        "--only",
        default=None,
        help="generate only these ids (comma-separated)",
    )
    ins.add_argument(
        "--force", action="store_true", help="regenerate even if a .png exists"
    )
    ins.add_argument(
        "--dry-run",
        action="store_true",
        help="write composed prompts only; no API call, no token needed",
    )
    ins.add_argument(
        "--review", action="store_true", help="also write a review.html grid"
    )

    args = p.parse_args(argv)

    if args.cmd == "init":
        from .scaffold import init_project  # noqa: PLC0415 — keep import local

        created = init_project(args.dest, force=args.force)
        for f in created:
            rich_print(f"created {f}")
        if not created:
            rich_print(f"{args.dest}: nothing to do (all files exist; use --force)")
        else:
            rich_print(
                f"\nProject ready in {args.dest}. Next:\n"
                f"  cmf render {args.dest / 'pages' / 'hello.yaml'}"
            )
    elif args.cmd in ("render", "scene"):
        lib = Library(args.library) if args.library else None
        scenes = SceneLibrary(args.scenes) if args.scenes else None
        px = PixelLibrary(args.pixel_dir) if args.pixel_dir else None
        fn = render_spec if args.cmd == "render" else render_scene
        out = args.out or _default_out(args.spec.stem)
        try:
            fn(args.spec, out, library=lib, scenes=scenes, pixel_library=px)
        except ValueError as e:
            rich_print(f"{args.spec}: {e}")
            return 1
        rich_print(f"wrote {out}")
    elif args.cmd == "validate":
        lib = Library(args.library) if args.library else None
        scenes = SceneLibrary(args.scenes) if args.scenes else None
        px = PixelLibrary(args.pixel_dir) if args.pixel_dir else None
        problems = validate_spec(
            args.spec, library=lib, scenes=scenes, pixel_library=px
        )
        if problems:
            rich_print(f"{args.spec}: {len(problems)} problem(s)")
            for msg in problems:
                rich_print(f"  - {msg}")
            return 1
        rich_print(f"{args.spec}: ok")
        return 0
    elif args.cmd == "panel":
        lib = Library(args.library) if args.library else None
        scenes = SceneLibrary(args.scenes) if args.scenes else None
        px = PixelLibrary(args.pixel_dir) if args.pixel_dir else None
        if args.all:
            out = args.out or (OUTPUT_DIR / f"{args.spec.stem}-panels-{_stamp()}")
            for o in render_all_panels(
                args.spec,
                out,
                library=lib,
                scenes=scenes,
                pixel_library=px,
                scale=args.scale,
            ):
                rich_print(f"wrote {o}")
        else:
            out = args.out or _default_out(
                f"{args.spec.stem}-r{args.row}c{args.col}"
            )
            render_panel(
                args.spec,
                out,
                args.row,
                args.col,
                library=lib,
                scenes=scenes,
                scale=args.scale,
                pixel_library=px,
            )
            rich_print(f"wrote {out}")
    elif args.cmd == "character":
        lib = Library(args.library)
        char = lib.get(args.name)
        selection, pose = _parse_selection(char, args.selections, args.pose)
        out = args.out or _default_out(args.name)
        render_character(
            args.name,
            out,
            selection,
            pose=pose,
            library=lib,
            scale=args.scale,
            bg=args.bg,
            flip=args.flip,
        )
        rich_print(f"wrote {out}")
        # a smaller PNG alongside it, sized for Claude to read with fewer tokens
        if args.thumb_px > 0:
            thumb = out.with_name(f"{out.stem}.small.png")
            thumb_scale = min(args.scale, args.thumb_px / char.resolve_pose(pose).w)
            render_character(
                args.name,
                thumb,
                selection,
                pose=pose,
                library=lib,
                scale=thumb_scale,
                bg=args.bg,
                flip=args.flip,
            )
            rich_print(f"wrote {thumb}")
    elif args.cmd == "characters":
        lib = Library(args.library)
        json.dump(lib.manifest(), sys.stdout, indent=2, ensure_ascii=False)
        rich_print()
    elif args.cmd == "scenes":
        scenes = SceneLibrary(args.scenes)
        json.dump(scenes.manifest(), sys.stdout, indent=2, ensure_ascii=False)
        rich_print()
    elif args.cmd == "inspire":
        from .inspire import generate  # noqa: PLC0415 — lazy: keeps Replicate optional

        only = {s.strip() for s in args.only.split(",")} if args.only else None
        out = generate(
            args.references,
            args.out,
            theme_path=args.theme,
            only=only,
            force=args.force,
            review=args.review,
            dry_run=args.dry_run,
        )
        rich_print(f"wrote {len(out)} file(s)")


if __name__ == "__main__":
    main()
