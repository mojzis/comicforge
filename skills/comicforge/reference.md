# ComicForge Authoring Guide

This guide covers everything you need to author comics with ComicForge — for both
humans and LLMs. The [SKILL.md](SKILL.md) file is the quick-reference contract;
this document goes deeper on structure, paths, and how all the pieces fit together.

---

## Engine + self-contained projects

ComicForge is a content-free engine plus self-contained projects. There is **no
shared asset library** — every project owns all of its own art:

```
comicforge/          The engine — pure code, ships no art of any kind.
examples/<name>/     A self-contained comic project: its own characters,
                     scenes, pixel art, and page specs. Nothing is shared.
```

A real downstream project just does `pip install comicforge` and creates the same
four asset folders; none of the example art ships with the engine. The `examples/`
directory is where we develop against the engine the same way a downstream project
would.

### `comicforge/` — the engine

The `comicforge/` package is the rendering engine. It loads assets, composes SVG,
and writes output. It contains **no concrete content** — no hardcoded characters,
no default scenes, no built-in sprites. All asset directories must be provided
explicitly (via the spec or CLI flags).

Modules:
- `library.py` — loads characters, stacks overlays, places them in panels
- `scene.py` — loads scene backgrounds, scales them to cover a panel/canvas
- `pixelart.py` — resolves pixel-art sprites from a directory or inline spec
- `render.py` — composes full pages, individual panels, and standalone scenes
- `bubbles.py` — speech, thought, and shout bubbles with word-wrap and tails
- `cli.py` — the `comicforge` command and its subcommands

### A project — `examples/<name>/`

Each project is one directory owning everything it needs. Page specs live under
`pages/` and point at the sibling asset folders one level up:

```
examples/pes/
  characters/          Character art: an identity that owns one or more poses
    tom/               flat (single pose): everything in one viewBox
      base.svg
      face-neutral.svg
      face-happy.svg
      arms-down.svg
      ...
      character.yaml
    bara/              posed: shared faces at root + a body per pose
      character.yaml
      face-neutral.svg     shared, re-anchored onto each pose
      face-happy.svg
      poses/
        sit/  { pose.yaml, base.svg }
        walk/ { pose.yaml, base.svg }
  scenes/              Scene backgrounds: base SVG + overlay SVGs + scene.yaml
    dvur/
      base.svg
      weather-clear.svg
      weather-rain.svg
      scene.yaml
    pokoj/
      base.svg
      scene.yaml
  pixel/               Pixel-art sprites: one YAML file per sprite
    heart.yaml
    sun.yaml
    star.yaml
    bone.yaml
  pages/               The comic specs
    slepice.yaml        2×2 comic page — Tom and Bára watch chickens
    kosticka.yaml       Strip with scenes, pixel art, and multiple bubble types
    dvur-scene.yaml     Standalone illustration — single scene filling the canvas
```

Each spec references its project's assets via relative paths (`../characters`,
`../scenes`, `../pixel`).

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

For example, `examples/pes/pages/slepice.yaml` contains:
```yaml
library: "../characters"
pixel_dir: "../pixel"
```

When you run from the repo root:
```bash
cmf render examples/pes/pages/slepice.yaml -o out.png
```

The engine resolves `../characters` relative to `examples/pes/pages/` — arriving
at `examples/pes/characters`. This means you can always run from the repo root
regardless of where specs live.

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

A character is an **identity** (name, label, …) that owns one or more **poses**.
A pose is a body drawn in its own viewBox; expressions (`face`, …) can be *shared*
across poses, authored once. There are two on-disk shapes.

### Single-pose (flat)

The classic layout — everything in one viewBox:

```
<project>/characters/<name>/
  base.svg                  The body drawn in a fixed local viewBox
  <slot>-<variant>.svg      Overlays in the same viewBox (one per variant)
  character.yaml            Manifest: name, label, viewbox, slots, default
```

```yaml
# character.yaml
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

All SVG files (base + overlays) share **the same viewBox**. The engine strips each
to its inner markup and stacks base → overlays in the slot order from
`character.yaml`.

### Multiple poses

When the **body** changes between poses (legs differ sit vs walk), each pose gets
its own `base.svg`. Shared overlays (faces) live at the character root and are
re-registered onto each pose via an **anchor** — a reference point (typically the
head centre) they are drawn around.

```
<project>/characters/<name>/
  character.yaml            Identity + SHARED slots + default + pose list
  <slot>-<variant>.svg      SHARED overlays, drawn around the canonical anchor
  poses/
    <pose>/
      pose.yaml             viewbox, anchor, optional pose-specific slots/default
      base.svg              this pose's body
      <slot>-<variant>.svg  optional pose-specific overlays
```

```yaml
# character.yaml
name: bara
label: Bára
anchor: [120, 72]                 # canonical point the shared overlays are drawn around
slots:  {face: [neutral, happy]}  # SHARED across poses, re-anchored per pose
default: {pose: sit, face: neutral}
poses: [sit, walk]
```

```yaml
# poses/walk/pose.yaml
viewbox: [240, 180]
anchor: [132, 64]                 # where THIS pose's head-centre lands
slots:  {arms: [trot]}            # OPTIONAL — pose-specific slots + overlays
default: {arms: trot}
```

For each shared overlay the engine emits a `translate(pose.anchor − character.anchor)`
so one `face-happy.svg` re-registers onto every pose. **Translate-only**: keep the
head the same *size* across poses; only its position changes. A flat character is
just the posed model with one implicit pose at anchor `[0, 0]`.

### Composition and placement

`Character.compose_inner(selection, pose)` assembles, in draw order:
1. The chosen pose's `base.svg`
2. That pose's pose-specific overlays (in `pose.yaml` slot order)
3. The shared overlays (in `character.yaml` slot order), each wrapped in the
   anchor-translate

`Character.place(selection, cx, cy, height, flip, pose)` wraps the result in a `<g
transform>` that scales it to `height` px tall (using the pose's viewBox) and
centres it at `(cx, cy)`. Omit `pose` to use `default.pose`.

### Adding a pose or expression

- **New expression (shared):** draw it around the canonical anchor, save as
  `<name>/<slot>-<variant>.svg`, add the variant to `slots` in `character.yaml`.
- **New pose:** add `poses/<pose>/` with its own `base.svg` + `pose.yaml`
  (set its `anchor`), and list `<pose>` under `poses:`.
- **Flat character, new overlay:** save `<name>/<slot>-<variant>.svg` in the shared
  viewBox and add it to `slots`.

No code changes needed.

---

## Authoring a scene

A scene is a full-panel illustrated background. It follows the same model as a
character: `base.svg` + optional overlay files + `scene.yaml`.

### Directory layout

```
<project>/scenes/<name>/
  base.svg                  The background drawn in a fixed local viewBox
  <slot>-<variant>.svg      Optional: weather effects, props, etc.
  scene.yaml                Manifest
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
cmf scenes --scenes examples/pes/scenes
```

---

## Authoring pixel art

Pixel art is defined as a grid of characters mapped to colors. It can come from
the library or be defined inline in the spec.

### Project sprites (`<project>/pixel/<name>.yaml`)

Each file contains `grid` (list of equal-length strings) and `palette` (map of
character to hex color):

```yaml
# examples/pes/pixel/heart.yaml
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
# From the project's pixel/ dir (needs pixel_dir: in the spec):
pixel_dir: "../pixel"
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

Run all commands from the repo root with `cmf <cmd>`.

**Default output.** `render`, `scene`, `panel`, and `character` accept `-o`, but
when you omit it they write a timestamped file into the gitignored `output/` dir
(e.g. `output/slepice-20260614-191613.png`). Successive renders accumulate so you
can compare how a page or character evolved; pass `-o` to pin an exact path.

### `render` — render a comic page

```bash
cmf render <spec.yaml> [-o <output>]   # default: output/<spec>-<timestamp>.png
  [--library <dir>]    # override spec's library: key
  [--scenes  <dir>]    # override spec's scenes_dir: key
  [--pixel-dir <dir>]  # override spec's pixel_dir: key
```

Output format is determined by the file extension: `.svg`, `.png`, or `.pdf`.

```bash
cmf render examples/pes/pages/slepice.yaml -o slepice.png
cmf render examples/pes/pages/slepice.yaml -o slepice.pdf
```

### `scene` — render a standalone illustration

```bash
cmf scene <spec.yaml> [-o <output>]   # default: output/<spec>-<timestamp>.png
  [--library <dir>]
  [--scenes  <dir>]
  [--pixel-dir <dir>]
```

```bash
cmf scene examples/pes/pages/dvur-scene.yaml -o dvur.png
```

### `panel` — render individual panels for review

```bash
cmf panel <spec.yaml> [-o <output>]   # default: output/<spec>-r<R>c<C>-<ts>.png
  [--row 0] [--col 0]       # which panel (0-indexed)
  [--all]                   # render every panel into a directory
                            # (default: output/<spec>-panels-<ts>/)
  [--scale 0.5]             # size vs full-page (default 0.5 = low res)
  [--library <dir>]
  [--scenes  <dir>]
  [--pixel-dir <dir>]
```

```bash
cmf panel examples/pes/pages/slepice.yaml -o panel.png --row 0 --col 1
cmf panel examples/pes/pages/kosticka.yaml -o panels/ --all
```

### `character` — render one character on its own

Quick visual test of a single character — no page, no panel, just the composed
character cropped to its pose on a plain canvas.

```bash
cmf character <name> [selection ...] --library <dir>
  [-o <output>]             # default: output/<name>-<timestamp>.png
  [--pose <pose>]           # which pose (default: the character's default)
  [--scale 2.0]             # px per viewBox unit
  [--bg "#ffffff"]          # canvas background colour (white by default)
  [--flip]                  # mirror horizontally
  [--thumb-px 320]          # body width of the small companion PNG (0 to skip)
```

Each `selection` token is either a bare name — matched first against the
character's **poses**, then against the variants of any **slot** — or an explicit
`key=value` (`pose=walk`, `face=happy`). Unknown tokens error with the available
poses and slots listed.

Writes **two files**: the full render at `-o`, and a smaller `<stem>.small.png`
beside it (body ≈ `--thumb-px` wide) — read the small one to spend fewer tokens.

```bash
cmf character bara sit happy --library examples/pes/characters -o bara.png
cmf character bara pose=walk face=neutral --library examples/pes/characters
cmf character tom --library examples/pes/characters   # default pose -> tom.png
```

### `characters` — list a project's characters

```bash
cmf characters --library <dir>
```

The `--library` flag is **required** (no default). Prints a JSON manifest of every
character, its slots, available variants, and defaults.

```bash
cmf characters --library examples/pes/characters
```

### `scenes` — list a project's scenes

```bash
cmf scenes --scenes <dir>
```

The `--scenes` flag is **required** (no default). Prints a JSON manifest of every
scene and its slots.

```bash
cmf scenes --scenes examples/pes/scenes
```

### `inspire` — generate reference images from a theme + descriptions

Paints **inspiration** art (a reference to author SVG from), *not* shipped assets.
Reads a project theme (`theme.yaml`) and a list of descriptions (`references.yaml`),
composes one prompt per item, and calls the Replicate API.

```bash
cmf inspire <references.yaml> -o <out_dir>
  [--theme <theme.yaml>]   # default: theme.yaml beside the spec
  [--only id1,id2]         # generate only these ids
  [--force]                # regenerate even if a .png already exists
  [--dry-run]              # compose prompts only — no API call, no token
  [--review]               # also write a review.html grid of images + prompts
```

Each item writes `<out_dir>/<id>.png` + `<id>.prompt.txt`. `theme.yaml` and the
output dir default to siblings of the references spec.

**Theme** (`<project>/theme.yaml`) — applied to every image:

| key | meaning |
|---|---|
| `style` | the look, in words (prepended to every prompt) |
| `palette` | list of hex colors fed to the model as a color scale |
| `mood` | one-line mood/tone |
| `negative` | what to avoid; default discourages text/marks |
| `aspect_ratio` | e.g. `"1:1"` (default) |
| `model` | Replicate model id (default `google/imagen-3`) |

**References** (`<project>/references.yaml`) — a `items:` list (or a bare list).
Each entry needs an id (`id`/`name`) and a description (`prompt`/`description`/`desc`).

Live generation requires the optional extra and a token:

```bash
pip install "comicforge[inspire]"          # adds replicate + python-dotenv
export REPLICATE_API_TOKEN=...             # or put it in a .env beside the spec
cmf inspire examples/pes/references.yaml --review
cmf inspire examples/pes/references.yaml --dry-run   # no token needed
```

The composed prompt is `style` → `Subject: <prompt>` → palette → mood → negative,
joined by blank lines (preview it with `--dry-run` and the `.prompt.txt` sidecar).
Do **not** auto-vectorize the result — hand/LLM-author the SVG using it as a guide.

---

## Spec reference

For the full spec grammar, see [SKILL.md](SKILL.md). Key points:

- **Page-level keys**: `title`, `page` (A4/A5/letter/[w,h]), `px_per_mm`,
  `margin_mm`, `gutter_mm`, `library`, `scenes_dir`, `pixel_dir`
- **Rows and panels**: `rows[].height` (relative weight), `rows[].panels[].width`
  (relative weight), panel keys: `bg`, `scene`, `actors`, `pixel`, `bubbles`
- **Actor keys**: `char`, `pose` (optional; defaults to the character's default
  pose), per-slot variant keys (`face`, `arms`, etc.), `x`, `y`, `scale`, `flip`
- **Bubble keys**: `text`, `kind` (speech/thought/shout), `speaker`, optional
  `x`/`y`/`to`/`max_chars`/`fs`
- **Pixel keys**: `art` (library name) or `grid`+`palette`, plus `x`/`y`/`scale`

---

## Python API

```python
from comicforge import render_spec, render_scene, load_spec, PixelLibrary

# Render a full comic page
render_spec("examples/pes/pages/slepice.yaml", "slepice.png")

# Render a standalone scene
render_scene("examples/pes/pages/dvur-scene.yaml", "dvur.png")

# Load a spec dict for inspection
spec = load_spec("examples/pes/pages/slepice.yaml")

# Pass asset dirs explicitly (overrides spec keys)
from comicforge.library import Library
from comicforge.scene import SceneLibrary
lib = Library("examples/pes/characters")
scn = SceneLibrary("examples/pes/scenes")
px  = PixelLibrary("examples/pes/pixel")
render_spec("examples/pes/pages/kosticka.yaml", "out.png",
            library=lib, scenes=scn, pixel_library=px)
```

---

## Demo pages at a glance

All three pages live in the `examples/pes/` project.

| Page | Spec | Description |
|---|---|---|
| `slepice` | `examples/pes/pages/slepice.yaml` | 2×2 page — Tom tells Bára to watch the chickens. No scenes. Pixel: sun, bone, heart. |
| `kosticka` | `examples/pes/pages/kosticka.yaml` | Comic strip — scenes (`pokoj`, `dvur`), pixel art, speech/thought/shout bubbles. |
| `dvur-scene` | `examples/pes/pages/dvur-scene.yaml` | Standalone illustration — farmyard, Tom and Bára. Render with `comicforge scene`. |

Render all demos from the repo root:
```bash
cmf render examples/pes/pages/slepice.yaml   -o slepice.png
cmf render examples/pes/pages/kosticka.yaml  -o kosticka.png
cmf scene  examples/pes/pages/dvur-scene.yaml -o dvur.png
```
