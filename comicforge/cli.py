"""Command line interface.

    python -m comicforge render examples/hello.yaml -o out.pdf
    python -m comicforge characters          # print library contract as JSON
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .render import render_spec, DEFAULT_LIB
from .library import Library


def main(argv=None):
    p = argparse.ArgumentParser(prog="comicforge")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="render a comic spec")
    r.add_argument("spec", type=Path)
    r.add_argument("-o", "--out", type=Path, required=True,
                   help="output .svg / .png / .pdf")
    r.add_argument("--library", type=Path, default=None)

    c = sub.add_parser("characters", help="print the character library contract")
    c.add_argument("--library", type=Path, default=None)

    args = p.parse_args(argv)

    if args.cmd == "render":
        lib = Library(args.library) if args.library else None
        render_spec(args.spec, args.out, library=lib)
        print(f"wrote {args.out}")
    elif args.cmd == "characters":
        lib = Library(args.library or DEFAULT_LIB)
        json.dump(lib.manifest(), sys.stdout, indent=2, ensure_ascii=False)
        print()


if __name__ == "__main__":
    main()
