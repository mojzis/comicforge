# ComicForge

A tiny, scriptable comic-page engine. Characters are a **base SVG + stackable
variant overlays** (faces, arms, …); a comic page is a **declarative YAML spec**;
output is **SVG / PNG / PDF**. Built so an LLM (or you) can author pages as plain
text — see [`AGENT.md`](AGENT.md).

## Install
```bash
uv sync                            # create .venv and install deps
uv run python tools/make_assets.py # (re)generate the seed character art
```

## Use
```bash
# render an example comic page
uv run comicforge render examples/slepice/page.yaml -o slepice.pdf
uv run comicforge render examples/slepice/page.yaml -o slepice.png

# render a standalone scene illustration (one background, no comic grid)
uv run comicforge scene examples/dvur-scene/scene.yaml -o dvur.png

# render individual panels at low res for quick review
uv run comicforge panel examples/slepice/page.yaml -o panel.png --row 0 --col 0
uv run comicforge panel examples/slepice/page.yaml -o panels/ --all --scale 0.5

# print the machine-readable contracts (characters / scenes, slots, variants)
uv run comicforge characters
uv run comicforge scenes
```

Or from Python:
```python
from comicforge import render_spec
render_spec("examples/slepice/page.yaml", "out.pdf")
```

## Library vs. projects
The **library** is the engine — the `comicforge/` package, the shared character
art under `characters/`, and the asset generator in `tools/`. **Projects** are the
comics you author with it: a project is just a directory holding one `page.yaml`
spec (and optionally its own `characters/` referenced via the spec's `library:`
key). The starter projects live under [`examples/`](examples/).

## How it fits together
```
characters/<name>/         base.svg + <slot>-<variant>.svg + character.yaml
scenes/<name>/             base.svg + <slot>-<variant>.svg + scene.yaml
comicforge/library.py      loads a character, stacks base+overlays, places it
comicforge/scene.py        loads a scene, stacks overlays, scales it to cover a box
comicforge/bubbles.py      speech / thought / shout bubbles with word-wrap + tail
comicforge/pixelart.py     grid+palette -> SVG sprite (heart/sun/star/bone + custom)
comicforge/render.py       row/panel pages + standalone scenes -> SVG -> PNG/PDF
comicforge/cli.py          `render`, `scene`, `characters`, `scenes` commands
tools/make_assets.py       procedurally writes the seed library (edit & re-run)
```

Characters and scenes share one model: a `base.svg` plus stackable
`<slot>-<variant>.svg` overlays in a common viewBox. Characters are *placed* at a
height; scenes are *scaled to cover* a panel or the whole illustration canvas.

## Design choices
- **Base + overlays** in one shared local canvas → "posing" is just choosing which
  overlay SVGs to stack. No rig math; each pose/expression is a small SVG you can
  edit by hand.
- **Declarative spec** → the whole agent surface is YAML + the `characters` JSON.
- **SVG all the way down**, rasterized only at the end → crisp vector PDF for print.

## Roadmap ideas
- A FastAPI + HTMX preview server (live re-render on spec edit).
- An MCP server exposing `list_characters` / `render_page` as tools.
- Part-anchored slots (separate eyes/mouth/limb pivots) for finer posing.
- Free-form panel shapes and a gutter/layout DSL.
- AI-image panels (drop a generated raster into a panel like pixel art).
