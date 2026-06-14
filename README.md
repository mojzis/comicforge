# ComicForge

A tiny, scriptable comic-page engine. Characters are a **base SVG + stackable
variant overlays** (faces, arms, …); a comic page is a **declarative YAML spec**;
output is **SVG / PNG / PDF**. Built so an LLM (or you) can author pages as plain
text — see the authoring skill [`skills/comicforge/SKILL.md`](skills/comicforge/SKILL.md)
for the full authoring contract and [`skills/comicforge/reference.md`](skills/comicforge/reference.md)
for a deeper reference. Working **on the engine** instead? See [`CLAUDE.md`](CLAUDE.md).

## Start a project

ComicForge ships no art and a project needs no Python — a project is just YAML
specs + SVG / pixel art that the CLI points at. Install the engine globally and
scaffold one:

```bash
uv tool install comicforge         # puts `cmf` on your PATH (no venv needed)
cmf init my-comic                  # scaffold characters/ scenes/ pixel/ pages/ + skill
cd my-comic && cmf render pages/hello.yaml
```

See [`docs/starting-a-project.md`](docs/starting-a-project.md) for the data-only
setup, version pinning, and when to make it a real Python project.

## Working on the engine

```bash
uv sync                            # create .venv and install deps
```

## Use

```bash
# render a comic page
cmf render examples/pes/pages/slepice.yaml -o slepice.png
cmf render examples/pes/pages/slepice.yaml -o slepice.pdf

# render a standalone scene illustration (one background, no comic grid)
cmf scene examples/pes/pages/dvur-scene.yaml -o dvur.png

# render individual panels at low res for quick review
cmf panel examples/pes/pages/slepice.yaml -o panel.png --row 0 --col 0
cmf panel examples/pes/pages/slepice.yaml -o panels/ --all --scale 0.5

# print the machine-readable contracts (characters / scenes, slots, variants)
cmf characters --library examples/pes/characters
cmf scenes --scenes examples/pes/scenes
```

Or from Python:
```python
from comicforge import render_spec
render_spec("examples/pes/pages/slepice.yaml", "out.pdf")
```

## How it fits together

ComicForge is a **content-free engine** plus **self-contained projects**. There is
no shared asset library: every project owns all of its own art. A real downstream
project just does `pip install comicforge` and brings its own characters — none of
the example art comes with the engine.

| Layer | Path | Purpose |
|---|---|---|
| Engine | `comicforge/` | Pure code — loads assets, composes SVG, writes output. No hardcoded content. |
| Project | `examples/<name>/` | A self-contained comic: its own characters, scenes, pixel art, and page specs. |

A project is one directory with four asset folders:

```
examples/pes/
  characters/tom/             flat: base.svg + <slot>-<variant>.svg + character.yaml
  characters/bara/            posed: shared faces + character.yaml + poses/{sit,walk}/
  scenes/{dvur,pokoj}/        base.svg + <slot>-<variant>.svg + scene.yaml
  pixel/{heart,sun,...}.yaml  grid + palette
  pages/
    slepice.yaml              2×2 comic — Tom and Bára watch chickens
    kosticka.yaml             Strip with scenes, pixel art, multiple bubble types
    dvur-scene.yaml           Standalone illustration (use `comicforge scene`)

comicforge/library.py         loads a character, stacks base+overlays, places it
comicforge/scene.py           loads a scene, stacks overlays, scales it to cover a box
comicforge/bubbles.py         speech / thought / shout bubbles with word-wrap + tail
comicforge/pixelart.py        grid+palette → SVG sprite
comicforge/render.py          row/panel pages + standalone scenes → SVG → PNG/PDF
comicforge/cli.py             `render`, `scene`, `panel`, `characters`, `scenes` commands
```

### Asset directories

Each spec declares where its assets live via top-level keys (paths are relative to
the spec file's directory). For a spec under `pages/`, the sibling asset folders
are one level up:

```yaml
library:    "../characters"   # character art
scenes_dir: "../scenes"       # scene backgrounds
pixel_dir:  "../pixel"        # pixel-art sprites
```

CLI flags (`--library`, `--scenes`, `--pixel-dir`) override spec keys and are
treated as relative to the current working directory.

See [`skills/comicforge/reference.md`](skills/comicforge/reference.md) for the full path
resolution rule, how to add characters/scenes/sprites, and the complete CLI reference.

## Design choices

- **Base + overlays** in one shared local canvas — "posing" is just choosing which
  overlay SVGs to stack. No rig math; each pose/expression is a small SVG you can
  edit by hand.
- **Declarative spec** — the whole agent surface is YAML + the `characters` JSON.
- **SVG all the way down**, rasterized only at the end — crisp vector PDF for print.
- **Content-free engine** — `comicforge/` ships no art. Each project owns all its
  own assets, so the engine is a dependency, not a content bundle.

## Roadmap ideas

- A FastAPI + HTMX preview server (live re-render on spec edit).
- An MCP server exposing `list_characters` / `render_page` as tools.
- Part-anchored slots (separate eyes/mouth/limb pivots) for finer posing.
- Free-form panel shapes and a gutter/layout DSL.
- AI-image panels (drop a generated raster into a panel like pixel art).
