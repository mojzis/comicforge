# Starting a project

ComicForge is a **content-free engine**: it ships no art and imports nothing
from your project. A project is just **data** — YAML specs plus SVG and pixel
art — that the `cmf` CLI points at.

So in the simplest and most common setup, your comic project is **not a Python
project at all**.

## The simple path: a data-only project

Install the engine once, globally:

```bash
uv tool install comicforge          # puts `cmf` and `comicforge` on your PATH
```

…or straight from the repository:

```bash
uv tool install git+https://github.com/mojzis/comicforge
```

Then scaffold and render:

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
  pixel/                      pixel-art sprites (grid + palette) — heart.yaml seeded
  pages/hello.yaml            a renderable starter page
  output/                     renders land here when you omit -o (gitignored)
  README.md  .gitignore
  .claude/skills/comicforge/  the authoring skill — lets Claude write specs for you
```

That is the whole project. No `pyproject.toml`, no virtualenv, no Python files.
Add your own characters under `characters/`, reference them as `actors` in a
page spec, and render.

`cmf init` is idempotent — re-running it over an existing project leaves your
files untouched. Pass `--force` to overwrite the scaffolded ones, which is how
you refresh the bundled skill after upgrading the engine.

[Your first comic](quickstart.md) walks through this with a character you draw
yourself.

## Version control

Commit everything except `output/`, which the scaffolded `.gitignore` already
excludes. The art is small, hand-authored SVG and YAML — it diffs, reviews and
merges like source code, which is much of the point.

## When you need more

| You want… | Setup |
|---|---|
| **Just to author and render comics** | The data-only project above. The default, and what most projects should stay as. |
| **A pinned engine version**, or the `inspire` extra | `uv tool install "comicforge[inspire]"`, **or** a tiny `pyproject.toml` with `comicforge==<version>` as its only dependency, run via `uv run cmf …`. Use this when two projects need *different* engine versions — `uv tool` installs are global and single-version. |
| **Your own render scripts or a generator** | A full Python project with `comicforge` as a library dependency: `from comicforge import render_spec`. Rare — see the [Python API](reference/python-api.md). |

A minimal pinned project:

```toml title="pyproject.toml"
[project]
name = "my-comic"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["comicforge==0.2.0"]
```

```bash
uv run cmf render pages/hello.yaml
```

## How paths resolve

This is worth getting straight once:

- Relative `library:` / `scenes_dir:` / `pixel_dir:` keys in a spec resolve
  against the **spec file's** directory. That is why a spec in `pages/` writes
  `library: "../characters"` and works from any working directory.
- A CLI flag (`--library`, `--scenes`, `--pixel-dir`) overrides the spec key and
  resolves against your **current working directory**.
- A page spec always needs a `library:`, even one pointing at an empty
  `characters/` directory. `scenes_dir:` and `pixel_dir:` are needed only when a
  spec actually uses a scene or a library sprite; inline pixel art needs
  neither.

## Structuring a bigger project

The four asset directories are a convention, not a rule — the engine only knows
what the spec keys point at. What tends to hold up as a project grows:

- **One directory per character**, named for the character, matching the `name:`
  in its `character.yaml`.
- **Pages under `pages/`**, one file per page or strip, named for the story
  beat rather than numbered.
- **A contact-sheet spec** per character — a page with one panel per variant,
  captioned with the variant name. It costs nothing to render and it is
  documentation that cannot go stale. See the
  [gallery](gallery.md#contact-sheets).
- **`references/` for generated inspiration art**, kept well away from
  `characters/`. It documents intent; it is never an asset.

## Authoring with Claude

The scaffolded `.claude/skills/comicforge/` is the authoring contract: open the
project in Claude Code and it can write and validate specs for you. See
[With Claude](claude.md).
