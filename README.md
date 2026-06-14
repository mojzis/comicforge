# ComicForge

A tiny, scriptable comic-page engine. Characters are a **base SVG + stackable
variant overlays** (faces, arms, …); a comic page is a **declarative YAML spec**;
output is **SVG / PNG / PDF**. Built so an LLM (or you) can author pages as plain
text — see [`AGENT.md`](AGENT.md) for the full authoring contract and
[`docs/authoring-guide.md`](docs/authoring-guide.md) for a deeper reference.

## Install

```bash
uv sync                            # create .venv and install deps
uv run python tools/make_assets.py # (re)generate the demo character/scene art
```

## Use

```bash
# render a comic page
uv run --active comicforge render projects/slepice/page.yaml -o slepice.png
uv run --active comicforge render projects/slepice/page.yaml -o slepice.pdf

# render a standalone scene illustration (one background, no comic grid)
uv run --active comicforge scene projects/dvur-scene/scene.yaml -o dvur.png

# render individual panels at low res for quick review
uv run --active comicforge panel projects/slepice/page.yaml -o panel.png --row 0 --col 0
uv run --active comicforge panel projects/slepice/page.yaml -o panels/ --all --scale 0.5

# print the machine-readable contracts (characters / scenes, slots, variants)
uv run --active comicforge characters --library library/characters
uv run --active comicforge scenes --scenes projects/_scenes
```

Or from Python:
```python
from comicforge import render_spec
render_spec("projects/slepice/page.yaml", "out.pdf")
```

## How it fits together

ComicForge is three separate layers:

| Layer | Path | Purpose |
|---|---|---|
| Engine | `comicforge/` | Pure code — loads assets, composes SVG, writes output. No hardcoded content. |
| Library | `library/` | Reusable shared assets: characters and pixel-art sprites. |
| Projects | `projects/<name>/` | A specific comic: its spec files, scenes, and asset references. |

```
library/
  characters/{tom,bara}/     base.svg + <slot>-<variant>.svg + character.yaml
  pixel/{heart,sun,...}.yaml  grid + palette

projects/
  slepice/page.yaml           2×2 comic — Tom and Bára watch chickens
  kosticka/page.yaml          Strip with scenes, pixel art, multiple bubble types
  dvur-scene/scene.yaml       Standalone illustration (use `comicforge scene`)
  _scenes/{dvur,pokoj}/       Shared scene backgrounds referenced by projects above

comicforge/library.py         loads a character, stacks base+overlays, places it
comicforge/scene.py           loads a scene, stacks overlays, scales it to cover a box
comicforge/bubbles.py         speech / thought / shout bubbles with word-wrap + tail
comicforge/pixelart.py        grid+palette → SVG sprite; loads sprites from library/pixel
comicforge/render.py          row/panel pages + standalone scenes → SVG → PNG/PDF
comicforge/cli.py             `render`, `scene`, `panel`, `characters`, `scenes` commands
tools/make_assets.py          procedurally writes the demo art (edit and re-run)
```

### Asset directories

Each spec declares where its assets live via top-level keys (paths are relative to
the spec file's directory):

```yaml
library:    "../../library/characters"   # character art
scenes_dir: "../../projects/_scenes"     # scene backgrounds
pixel_dir:  "../../library/pixel"        # pixel-art sprites
```

CLI flags (`--library`, `--scenes`, `--pixel-dir`) override spec keys and are
treated as relative to the current working directory.

See [`docs/authoring-guide.md`](docs/authoring-guide.md) for the full path
resolution rule, how to add characters/scenes/sprites, and the complete CLI reference.

## Design choices

- **Base + overlays** in one shared local canvas — "posing" is just choosing which
  overlay SVGs to stack. No rig math; each pose/expression is a small SVG you can
  edit by hand.
- **Declarative spec** — the whole agent surface is YAML + the `characters` JSON.
- **SVG all the way down**, rasterized only at the end — crisp vector PDF for print.
- **Content-free engine** — `comicforge/` ships no art. Assets live in `library/`
  and `projects/`, so the engine is a dependency, not a content bundle.

## Roadmap ideas

- A FastAPI + HTMX preview server (live re-render on spec edit).
- An MCP server exposing `list_characters` / `render_page` as tools.
- Part-anchored slots (separate eyes/mouth/limb pivots) for finer posing.
- Free-form panel shapes and a gutter/layout DSL.
- AI-image panels (drop a generated raster into a panel like pixel art).
