"""Command line interface.

python -m comicforge render projects/slepice/page.yaml -o out.pdf
python -m comicforge scene  projects/dvur-scene/scene.yaml -o out.png
python -m comicforge characters --library library/characters
python -m comicforge scenes --scenes projects/_scenes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .library import Library
from .pixelart import PixelLibrary
from .render import render_all_panels, render_panel, render_scene, render_spec
from .scene import SceneLibrary


def main(argv=None):
    p = argparse.ArgumentParser(prog="comicforge")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="render a comic page spec")
    r.add_argument("spec", type=Path)
    r.add_argument(
        "-o", "--out", type=Path, required=True, help="output .svg / .png / .pdf"
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

    s = sub.add_parser("scene", help="render a standalone scene illustration")
    s.add_argument("spec", type=Path)
    s.add_argument(
        "-o", "--out", type=Path, required=True, help="output .svg / .png / .pdf"
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
        required=True,
        help="output file, or a directory when --all",
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

    args = p.parse_args(argv)

    if args.cmd in ("render", "scene"):
        lib = Library(args.library) if args.library else None
        scenes = SceneLibrary(args.scenes) if args.scenes else None
        px = PixelLibrary(args.pixel_dir) if args.pixel_dir else None
        fn = render_spec if args.cmd == "render" else render_scene
        fn(args.spec, args.out, library=lib, scenes=scenes, pixel_library=px)
        print(f"wrote {args.out}")
    elif args.cmd == "panel":
        lib = Library(args.library) if args.library else None
        scenes = SceneLibrary(args.scenes) if args.scenes else None
        px = PixelLibrary(args.pixel_dir) if args.pixel_dir else None
        if args.all:
            for o in render_all_panels(
                args.spec,
                args.out,
                library=lib,
                scenes=scenes,
                pixel_library=px,
                scale=args.scale,
            ):
                print(f"wrote {o}")
        else:
            render_panel(
                args.spec,
                args.out,
                args.row,
                args.col,
                library=lib,
                scenes=scenes,
                scale=args.scale,
                pixel_library=px,
            )
            print(f"wrote {args.out}")
    elif args.cmd == "characters":
        lib = Library(args.library)
        json.dump(lib.manifest(), sys.stdout, indent=2, ensure_ascii=False)
        print()
    elif args.cmd == "scenes":
        scenes = SceneLibrary(args.scenes)
        json.dump(scenes.manifest(), sys.stdout, indent=2, ensure_ascii=False)
        print()


if __name__ == "__main__":
    main()
