"""`comicforge init` — scaffold a data-only ComicForge project.

A downstream project needs no Python: it is a directory of YAML specs and
SVG / pixel art that the installed ``cmf`` CLI points at. This module lays out
that directory — the four asset folders, a renderable starter page, a project
README, and a copy of the authoring skill so an LLM can write specs for you.
"""

from __future__ import annotations

from pathlib import Path

# The authoring skill ships inside the wheel (force-included at comicforge/_skill,
# see pyproject.toml); in a source checkout it still lives at the repo root.
_BUNDLED_SKILL = Path(__file__).parent / "_skill"
_DEV_SKILL = Path(__file__).resolve().parent.parent / "skills" / "comicforge"

_GITKEEP = "# keep this (empty) directory under version control\n"

_HEART_SPRITE = """\
# A starter pixel-art sprite. Reference it from a spec as {art: heart, ...}.
palette:
  r: "#e8554d"
grid:
  - ".rr.rr."
  - "rrrrrrr"
  - "rrrrrrr"
  - ".rrrrr."
  - "..rrr.."
  - "...r..."
"""

_STARTER_PAGE = """\
# Your first page. Render it with:
#   cmf render pages/hello.yaml            -> output/hello-<timestamp>.png
#   cmf render pages/hello.yaml -o hi.pdf
#
# Everything here is plain data — this project needs no Python. Paths resolve
# relative to THIS file, so `library: ../characters` works from any cwd.
title: "Hello, ComicForge"
page: A5
library: "../characters"     # add characters here, then place them as `actors`
pixel_dir: "../pixel"

rows:
  - panels:
      - bubbles:
          - text: "Edit pages/hello.yaml to build your first page!"
            kind: speech
        pixel:
          - {art: heart, x: 0.5, y: 0.72, scale: 0.32}
      # Once you add a character (see .claude/skills/comicforge/SKILL.md),
      # place it in a panel like this:
      # - actors:
      #     - {char: yourchar, face: happy, x: 0.5, y: 0.7, scale: 0.85}
"""

_README = """\
# {name} — a ComicForge project

A **data-only** ComicForge project: YAML specs + SVG / pixel art, no Python.

## Setup (once)

    uv tool install comicforge        # puts `cmf` / `comicforge` on your PATH

## Render

    cmf render pages/hello.yaml        # -> output/hello-<timestamp>.png
    cmf render pages/hello.yaml -o hello.pdf
    cmf validate pages/hello.yaml      # check a spec without rendering

## Layout

    characters/   one dir per character (base.svg + overlays + character.yaml)
    scenes/       one dir per scene background
    pixel/        pixel-art sprites (grid + palette)
    pages/        the page / scene specs you render
    output/       renders land here when you omit -o (gitignored)
    .claude/skills/comicforge/   the authoring skill — lets Claude write specs

Paths in a spec resolve relative to the spec file, so `library: ../characters`
works from anywhere. See the skill for the full spec grammar, and add your own
characters under `characters/` to start placing actors.
"""

_GITIGNORE = "output/\n"

_ASSET_DIRS = ("characters", "scenes", "pixel", "pages")


def skill_src() -> Path | None:
    """Locate the authoring skill: bundled in the wheel, else the source tree."""
    if _BUNDLED_SKILL.is_dir():
        return _BUNDLED_SKILL
    if _DEV_SKILL.is_dir():
        return _DEV_SKILL
    return None


def _write(path: Path, text: str, *, force: bool, created: list[Path]) -> None:
    """Write *text* to *path* unless it exists and *force* is False."""
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    created.append(path)


def init_project(dest: str | Path, *, force: bool = False) -> list[Path]:
    """Scaffold a data-only project at *dest*. Returns the files written.

    Idempotent: existing files are left untouched unless *force* is True, so
    re-running over a project never clobbers your art.
    """
    dest = Path(dest)
    created: list[Path] = []

    for d in _ASSET_DIRS:
        _write(dest / d / ".gitkeep", _GITKEEP, force=force, created=created)

    _write(dest / "pixel" / "heart.yaml", _HEART_SPRITE, force=force, created=created)
    _write(dest / "pages" / "hello.yaml", _STARTER_PAGE, force=force, created=created)
    _write(
        dest / "README.md",
        _README.format(name=dest.resolve().name),
        force=force,
        created=created,
    )
    _write(dest / ".gitignore", _GITIGNORE, force=force, created=created)

    src = skill_src()
    if src is not None:
        skill_dest = dest / ".claude" / "skills" / "comicforge"
        for f in sorted(src.glob("*")):
            if f.is_file():
                _write(
                    skill_dest / f.name,
                    f.read_text(encoding="utf-8"),
                    force=force,
                    created=created,
                )

    return created
