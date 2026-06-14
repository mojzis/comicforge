# Starting a ComicForge project

ComicForge is a **content-free engine**: it ships no art and imports nothing
from your project. A project is just **data** — YAML specs plus SVG / pixel
art — that the `cmf` CLI points at. So in the simplest setup your project is
**not a Python project at all**.

## The simple path: a data-only project

Install the engine once, globally, as a [uv tool](https://docs.astral.sh/uv/):

```bash
uv tool install comicforge          # puts `cmf` and `comicforge` on your PATH
# from a git source instead:
uv tool install git+https://github.com/mojzis/comicforge
```

Scaffold a project and render it:

```bash
cmf init my-comic
cd my-comic
cmf render pages/hello.yaml          # -> output/hello-<timestamp>.png
```

`cmf init` lays out everything you need:

```
my-comic/
  characters/                 one dir per character (base.svg + overlays + character.yaml)
  scenes/                     one dir per scene background
  pixel/                      pixel-art sprites (grid + palette)  — heart.yaml seeded
  pages/hello.yaml            a renderable starter page
  output/                     renders land here when you omit -o (gitignored)
  README.md  .gitignore
  .claude/skills/comicforge/  the authoring skill — lets Claude write specs for you
```

That's the whole project. No `pyproject.toml`, no virtualenv, no Python files.
Add your own characters under `characters/`, reference them as `actors` in a
page spec, and render. Paths in a spec resolve relative to the **spec file**, so
`library: ../characters` works regardless of your current directory.

`cmf init` is idempotent — re-running it over an existing project leaves your
files untouched (pass `--force` to overwrite the scaffolded ones).

## When you need more

| You want… | Setup |
|---|---|
| **Just to author and render comics** | Data-only project (above). The default. |
| **A pinned engine version** for reproducibility, or the `inspire` extra | `uv tool install "comicforge[inspire]"`, **or** a tiny `pyproject.toml` with `comicforge==<version>` as the only dep and run via `uv run cmf …`. Use this when two projects need *different* engine versions — `uv tool` installs are global / single-version. |
| **Your own render scripts or a generator** | A full Python project with `comicforge` as a library dependency: `from comicforge import render_spec`. Rare. |

## How paths resolve (worth knowing)

- Relative `library:` / `scenes_dir:` / `pixel_dir:` keys in a spec resolve
  against the **spec file's** directory.
- A CLI flag (`--library`, `--scenes`, `--pixel-dir`) overrides the spec key and
  resolves against your current working directory.
- A page spec always needs a `library:` (even one pointing at an empty
  `characters/` dir); `scenes_dir:` and `pixel_dir:` are only needed when a spec
  actually uses a scene or a sprite from disk. Inline pixel art needs no dir.

## Authoring with Claude

The scaffolded `.claude/skills/comicforge/` is the authoring contract: open the
project in Claude Code and it can write and validate specs for you. Keep it in
sync by re-running `cmf init --force` after upgrading the engine, or copy
`skills/comicforge/` from the engine repo.
