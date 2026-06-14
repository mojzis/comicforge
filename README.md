# ComicForge

A tiny, scriptable comic-page engine. Characters are a **base SVG + stackable
variant overlays** (faces, arms, …); a comic page is a **declarative YAML spec**;
output is **SVG / PNG / PDF**. Built so an LLM (or you) can author pages as plain
text — see [`AGENT.md`](AGENT.md).

## Install
```bash
pip install cairosvg pyyaml        # the only deps
python tools/make_assets.py        # (re)generate the seed character art
```

## Use
```bash
# render the example
python -m comicforge render examples/hello.yaml -o hello.pdf
python -m comicforge render examples/hello.yaml -o hello.png

# print the machine-readable character contract (characters, slots, variants)
python -m comicforge characters
```

Or from Python:
```python
from comicforge import render_spec
render_spec("examples/hello.yaml", "out.pdf")
```

## How it fits together
```
characters/<name>/         base.svg + <slot>-<variant>.svg + character.yaml
comicforge/library.py      loads a character, stacks base+overlays, places it
comicforge/bubbles.py      speech / thought / shout bubbles with word-wrap + tail
comicforge/pixelart.py     grid+palette -> SVG sprite (heart/sun/star/bone + custom)
comicforge/render.py       A4 row/panel layout -> one SVG -> PNG/PDF (cairosvg)
comicforge/cli.py          `render` and `characters` commands
tools/make_assets.py       procedurally writes the seed library (edit & re-run)
```

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
