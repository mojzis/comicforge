# ComicForge Authoring Guide

This guide covers everything you need to author comics with ComicForge — for both
humans and LLMs. The [AGENT.md](../AGENT.md) file is the quick-reference contract;
this document goes deeper on structure, paths, and how all the pieces fit together.

---

## The three-layer model

ComicForge separates content from engine cleanly:

```
comicforge/        The engine — pure code, ships no art of any kind.
library/           Reusable, shareable assets: characters and pixel-art sprites.
projects/<name>/   A specific comic project: its specs, scenes, and nothing else.
```

### `comicforge/` — the engine

The `comicforge/` package is the rendering engine. It loads assets, composes SVG,
and writes output. It contains **no concrete content** — no hardcoded characters,
no default scenes, no built-in sprites. All asset directories must be provided
explicitly (via the spec or CLI flags).

Modules:
- `library.py` — loads characters, stacks overlays, places them in panels
- `scene.py` — loads scene backgrounds, scales them to cover a panel/canvas
- `pixelart.py` — resolves pixel-art sprites from a library or inline spec
- `render.py` — composes full pages, individual panels, and standalone scenes
- `bubbles.py` — speech, thought, and shout bubbles with word-wrap and tails
- `cli.py` — the `comicforge` command and its subcommands

### `library/` — reusable assets

Shared building blocks used across all projects:

```
library/
  characters/          Character art: base SVG + overlay SVGs + character.yaml
    tom/
      base.svg
      face-neutral.svg
      face-happy.svg
      arms-down.svg
      ...
      character.yaml
    bara/
      ...
  pixel/               Pixel-art sprites: one YAML file per sprite
    heart.yaml
    sun.yaml
    star.yaml
    bone.yaml
```

Characters and pixel-art sprites belong in `library/` because they are reusable
across every project. They are **not** tied to any specific comic.

### `projects/<name>/` — a comic project

Each subdirectory of `projects/` is one comic. A project owns:
- Its **spec file(s)** (`page.yaml`, `scene.yaml`)
- Its **scenes** (scene backgrounds specific to this story)

Projects reference assets from `library/` via relative paths in the spec.

Current projects:

```
projects/
  slepice/
    page.yaml           2×2 comic page — Tom and Bára watch chickens
  kosticka/
    page.yaml           Comic strip with scenes, pixel art, and multiple bubble types
  dvur-scene/
    scene.yaml          Standalone illustration — single scene filling the canvas
  _scenes/             Shared scene backgrounds (used by kosticka and dvur-scene)
    dvur/
      base.svg
      weather-clear.svg
      weather-rain.svg
      scene.yaml
    pokoj/
      base.svg
      scene.yaml
```

The `_scenes/` directory is a shared scenes pool inside `projects/`. Both
`kosticka` and `dvur-scene` reference it via `scenes_dir: "../../projects/_scenes"`
in their specs.

---

## Asset loading and path resolution

The engine needs three asset directories. Each can be provided in the spec file or
via a CLI flag:

| Purpose | Spec key | CLI flag |
|---|---|---|
| Character library | `library:` | `--library` |
| Scene backgrounds | `scenes_dir:` | `--scenes` |
| Pixel-art sprites | `pixel_dir:` | `--pixel-dir` |

### Path resolution rule

**Relative paths in the spec are resolved against the spec file's directory.**

For example, `projects/slepice/page.yaml` contains:
```yaml
library: "../../library/characters"
pixel_dir: "../../library/pixel"
```

When you run from the repo root:
```bash
uv run --active comicforge render projects/slepice/page.yaml -o out.png
```

The engine resolves `../../library/characters` relative to
`projects/slepice/` — arriving at `library/characters` from the repo root. This
means you can always run from the repo root regardless of where specs live.

**CLI flags are used as-is** (relative to your current working directory, or
absolute). A CLI flag overrides the spec key entirely.

### When a directory is missing

If `library:` is absent from the spec and `--library` was not passed, the engine
raises:
```
ValueError: library directory is required but was not provided.
Set 'library:' in the spec or pass the corresponding CLI flag.
```

If `scenes_dir:` is absent but the spec uses a `scene:` key in a panel, the engine
raises at render time when the scene is first accessed.

`pixel_dir:` is optional — you only need it when using `{art: <name>}` references.
Inline `{grid: [...], palette: {...}}` specs work with no pixel library at all.

---

## Authoring a character

A character is a directory inside `library/characters/` with three parts:

### Directory layout

```
library/characters/<name>/
  base.svg                  The body drawn in a fixed local viewBox
  <slot>-<variant>.svg      Overlays in the same viewBox (one per variant)
  character.yaml            Manifest: name, slots, defaults
```

### character.yaml

```yaml
name: tom                    # internal ID (must match directory name)
label: Tom                   # display name for the UI / manifest
viewbox: [200, 320]          # local canvas size [width, height]
default:
  face: neutral              # default variant for each slot (used when omitted in spec)
  arms: down
slots:
  arms: [down, wave, point, crossed, hips, thumbsup]
  face: [neutral, happy, surprised, sad, angry, laugh, wink]
```

### The shared-viewBox overlay model

All SVG files for a character (base + all overlays) share **the same viewBox
dimensions**. The engine strips each file down to its inner markup and stacks them
in the order the slots appear in `character.yaml`.

When rendering, `Character.compose_inner(selection)` assembles:
1. The base inner SVG (body)
2. Each slot's chosen variant (or the default) in manifest slot order

Then `Character.place(selection, cx, cy, height, flip)` wraps this in a `<g
transform>` that scales it so the character is `height` pixels tall and centres it
at `(cx, cy)` in panel coordinates.

### Adding a new pose or expression

1. Draw the overlay in the **same viewBox** as the existing overlays (e.g. `0 0 200 320`)
2. Save it as `library/characters/<name>/<slot>-<variant>.svg`
3. Add the variant name to the matching slot list in `character.yaml`

Example — adding a "thinking" arm pose to Tom:
```bash
# 1. Create the SVG file
vim library/characters/tom/arms-thinking.svg

# 2. Add "thinking" to the arms list in character.yaml
#    slots:
#      arms: [down, wave, point, crossed, hips, thumbsup, thinking]
```

No code changes needed.

---

## Authoring a scene

A scene is a full-panel illustrated background. It follows the same model as a
character: `base.svg` + optional overlay files + `scene.yaml`.

### Directory layout

```
projects/_scenes/<name>/
  base.svg                  The background drawn in a fixed local viewBox
  <slot>-<variant>.svg      Optional: weather effects, props, etc.
  scene.yaml                Manifest
```

Or inside a project that owns the scene:
```
projects/<myproject>/scenes/<name>/
  ...
```

### scene.yaml

```yaml
name: dvur
label: Dvůr
viewbox: [320, 200]
default:
  weather: clear
slots:
  weather: [clear, rain]
```

A scene with no slots has only `name`, `label`, and `viewbox`.

### Cover-scaling behavior

Scenes are rendered with `cover` scaling: the scene is scaled so its **smaller
dimension fits** and the other dimension may overflow, always filling the full panel
with no empty borders. The scene is centred within the panel.

### Using a scene in a spec

```yaml
# In a panel:
scene: dvur                           # default slots
scene: {name: dvur, weather: rain}    # pick a slot variant

# In a standalone scene spec:
scene:
  name: dvur
  weather: clear
scale: 3                              # px per scene unit (canvas = viewbox × scale)
```

Confirm available scenes and slots with:
```bash
uv run --active comicforge scenes --scenes projects/_scenes
```

---

## Authoring pixel art

Pixel art is defined as a grid of characters mapped to colors. It can come from
the library or be defined inline in the spec.

### Library sprites (`library/pixel/<name>.yaml`)

Each file contains `grid` (list of equal-length strings) and `palette` (map of
character to hex color):

```yaml
# library/pixel/heart.yaml
palette:
  R: "#e8556d"
  r: "#b83e54"
grid:
  - ".RR..RR."
  - "RRRRRRRR"
  - "RRRRRRRR"
  - "RRRRRRRR"
  - ".RRRRRR."
  - "..RRRR.."
  - "...RR..."
```

The transparent-cell convention: `.` (period) or ` ` (space) = transparent.
Any other character maps to a color in `palette`.

### Inline sprites

Define the grid and palette directly in the panel spec:

```yaml
pixel:
  - grid: ["....", ".RR.", ".RR.", "...."]
    palette: {R: "#e8556d"}
    x: 0.5
    y: 0.5
    scale: 0.3
```

Inline sprites require no library. The `pixel_dir:` spec key is only needed when
using `{art: <name>}` references.

### Using pixel art in a spec

```yaml
# From the library (needs pixel_dir: in the spec):
pixel_dir: "../../library/pixel"
# ...
pixel:
  - art: heart
    x: 0.8
    y: 0.25
    scale: 0.18

# Inline (no pixel_dir needed):
pixel:
  - grid: ["XX", "XX"]
    palette: {X: "#ff0000"}
    x: 0.5
    y: 0.5
    scale: 0.2
```

Coordinates: `x`/`y` are panel fractions (0–1); `scale` = sprite height as a
fraction of panel height. Multiple pixel items can appear in one panel.

---

## CLI reference

Run all commands from the repo root with `uv run --active comicforge <cmd>`.

### `render` — render a comic page

```bash
uv run --active comicforge render <spec.yaml> -o <output>
  [--library <dir>]    # override spec's library: key
  [--scenes  <dir>]    # override spec's scenes_dir: key
  [--pixel-dir <dir>]  # override spec's pixel_dir: key
```

Output format is determined by the file extension: `.svg`, `.png`, or `.pdf`.

```bash
uv run --active comicforge render projects/slepice/page.yaml -o slepice.png
uv run --active comicforge render projects/slepice/page.yaml -o slepice.pdf
```

### `scene` — render a standalone illustration

```bash
uv run --active comicforge scene <spec.yaml> -o <output>
  [--library <dir>]
  [--scenes  <dir>]
  [--pixel-dir <dir>]
```

```bash
uv run --active comicforge scene projects/dvur-scene/scene.yaml -o dvur.png
```

### `panel` — render individual panels for review

```bash
uv run --active comicforge panel <spec.yaml> -o <output>
  [--row 0] [--col 0]       # which panel (0-indexed)
  [--all]                   # render every panel into a directory
  [--scale 0.5]             # size vs full-page (default 0.5 = low res)
  [--library <dir>]
  [--scenes  <dir>]
  [--pixel-dir <dir>]
```

```bash
uv run --active comicforge panel projects/slepice/page.yaml -o panel.png --row 0 --col 1
uv run --active comicforge panel projects/kosticka/page.yaml -o panels/ --all
```

### `characters` — list the character library

```bash
uv run --active comicforge characters --library <dir>
```

The `--library` flag is **required** (no default). Prints a JSON manifest of every
character, its slots, available variants, and defaults.

```bash
uv run --active comicforge characters --library library/characters
```

### `scenes` — list the scene library

```bash
uv run --active comicforge scenes --scenes <dir>
```

The `--scenes` flag is **required** (no default). Prints a JSON manifest of every
scene and its slots.

```bash
uv run --active comicforge scenes --scenes projects/_scenes
```

---

## Spec reference

For the full spec grammar, see [AGENT.md](../AGENT.md). Key points:

- **Page-level keys**: `title`, `page` (A4/A5/letter/[w,h]), `px_per_mm`,
  `margin_mm`, `gutter_mm`, `library`, `scenes_dir`, `pixel_dir`
- **Rows and panels**: `rows[].height` (relative weight), `rows[].panels[].width`
  (relative weight), panel keys: `bg`, `scene`, `actors`, `pixel`, `bubbles`
- **Actor keys**: `char`, per-slot variant keys (`face`, `arms`, etc.), `x`, `y`,
  `scale`, `flip`
- **Bubble keys**: `text`, `kind` (speech/thought/shout), `speaker`, optional
  `x`/`y`/`to`/`max_chars`/`fs`
- **Pixel keys**: `art` (library name) or `grid`+`palette`, plus `x`/`y`/`scale`

---

## Python API

```python
from comicforge import render_spec, render_scene, load_spec, PixelLibrary

# Render a full comic page
render_spec("projects/slepice/page.yaml", "slepice.png")

# Render a standalone scene
render_scene("projects/dvur-scene/scene.yaml", "dvur.png")

# Load a spec dict for inspection
spec = load_spec("projects/slepice/page.yaml")

# Pass asset dirs explicitly (overrides spec keys)
from comicforge.library import Library
from comicforge.scene import SceneLibrary
lib = Library("library/characters")
scn = SceneLibrary("projects/_scenes")
px  = PixelLibrary("library/pixel")
render_spec("projects/kosticka/page.yaml", "out.png",
            library=lib, scenes=scn, pixel_library=px)
```

---

## Demo projects at a glance

| Project | Spec | Description |
|---|---|---|
| `slepice` | `projects/slepice/page.yaml` | 2×2 page — Tom tells Bára to watch the chickens. No scenes. Pixel: sun, bone, heart. |
| `kosticka` | `projects/kosticka/page.yaml` | Comic strip — scenes (`pokoj`, `dvur`), pixel art, speech/thought/shout bubbles. |
| `dvur-scene` | `projects/dvur-scene/scene.yaml` | Standalone illustration — farmyard, Tom and Bára. Render with `comicforge scene`. |

Render all demos from the repo root:
```bash
uv run --active comicforge render projects/slepice/page.yaml   -o slepice.png
uv run --active comicforge render projects/kosticka/page.yaml  -o kosticka.png
uv run --active comicforge scene  projects/dvur-scene/scene.yaml -o dvur.png
```
