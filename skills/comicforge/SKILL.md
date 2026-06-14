---
name: comicforge
description: >
  Author comic pages and standalone illustrations as declarative YAML specs that
  ComicForge renders to SVG / PNG / PDF. Use this skill whenever the user wants to
  make a comic strip, comic page, cartoon panel, or single illustration with
  ComicForge — placing characters (base SVG + stackable face/arms overlays), scene
  backgrounds, speech/thought/shout bubbles, and pixel-art sprites in a row/panel
  grid. Also triggers on adding a new character, scene, or sprite to a ComicForge
  project, or on questions about the spec grammar, panel coordinates, or the
  `comicforge` CLI (`render`, `scene`, `panel`, `characters`, `scenes`).
---

# ComicForge — authoring comics from YAML

You write a **comic page as a YAML spec**; the engine renders it to SVG/PNG/PDF.
This file is the authoring contract. For deeper explanations (path resolution,
how to add characters/scenes, pixel-art format, Python API, full CLI reference)
see [`reference.md`](reference.md) in this skill directory.

## Loop

All art belongs to a **project** (e.g. `examples/pes/`) — there is no shared
library. A project owns `characters/`, `scenes/`, `pixel/`, and its page specs
under `pages/`. Paths below assume you are working inside one project.

1. Read the project's assets:
   - `uv run --active comicforge characters --library examples/pes/characters` → JSON
     of every character, its **slots**, **variants** per slot, and the defaults.
   - `uv run --active comicforge scenes --scenes examples/pes/scenes` → JSON of every
     scene background and its slots.
2. Write a spec under `pages/` (see grammar below). Spec-level keys declare where
   assets live, relative to the spec file (siblings are one level up):
   ```yaml
   library:    "../characters"
   scenes_dir: "../scenes"
   pixel_dir:  "../pixel"
   ```
3. Render:
   - comic page: `uv run --active comicforge render mystrip.yaml -o out.pdf`
   - single illustration: `uv run --active comicforge scene myscene.yaml -o out.png`
4. Look at the output; adjust `x` / `y` / `scale` / `to` and re-render.

## Coordinates

Every position inside a panel is a **fraction 0..1 of that panel**:
`x` = left→right, `y` = top→bottom. `(0.5, 0.5)` is the panel centre.
`scale` for actors/pixel art = height as a fraction of the panel height.

## Spec grammar

```yaml
title: "Optional page title"      # bold caption strip at the top
page: A4                          # A4 | A5 | letter | [w_mm, h_mm]
px_per_mm: 4                      # raster scale (vector PDF ignores it)
margin_mm: 14
gutter_mm: 6
library:    "../characters"   # path to character dir
scenes_dir: "../scenes"       # path to scenes dir (omit if no scenes used)
pixel_dir:  "../pixel"        # path to pixel-art dir (omit if inline only)

rows:                             # page is a stack of rows…
  - height: 1.0                   # relative row height (default 1)
    panels:                       # …each row is a left→right list of panels
      - width: 1.0                # relative panel width (default 1)
        bg: "#fbfaf6"             # optional flat panel background
        scene: dvur               # optional scene background (see below)
        actors: [ ... ]           # characters (drawn back→front in list order)
        pixel:  [ ... ]           # pixel-art sprites (drawn behind actors)
        bubbles:[ ... ]           # speech/thought/shout (drawn on top)
```

### actor

```yaml
- char: tom         # character name (from `comicforge characters`)
  pose: walk        # OPTIONAL: which body to draw; defaults to the character's default pose
  face: happy       # any slot -> a valid variant; omitted slots use defaults
  arms: wave
  x: 0.35           # centre (panel fraction)
  y: 0.62
  scale: 0.85       # height as fraction of panel height
  flip: false       # mirror horizontally (face the other way)
```

Slots and poses are per character. `tom` is single-pose with `face`
(neutral/happy/surprised/sad/angry/laugh/wink) and `arms`
(down/wave/point/crossed/hips/thumbsup); `bara` has poses `sit`/`walk` and a
shared `face` (neutral/happy). Omit `pose` to get the default. Some slots are
shared across poses, some are pose-specific — the manifest shows both. Always
confirm against `comicforge characters --library <project>/characters` — never
guess a pose or variant that isn't listed.

### scene (panel background)

A scene is a reusable illustrated background, scaled to *cover* the panel.

```yaml
scene: dvur                 # just the name…
scene: {name: dvur, weather: rain}   # …or pick scene slot variants
```

Confirm scenes/slots with `comicforge scenes --scenes <project>/scenes`.
Seeds in `examples/pes/`: `dvur` (farmyard, slot `weather: clear|rain`),
`pokoj` (room, no slots). Both live in `examples/pes/scenes/`.

## Standalone illustration (no comic grid)

Render one scene filling the whole canvas with actors/bubbles on top — good for
covers and single panels. Render with `comicforge scene file.yaml -o out.png`:

```yaml
title: "Optional"
scene: {name: dvur, weather: clear}
scale: 3                    # px per scene unit (canvas = scene viewbox × scale)
library:    "../characters"
scenes_dir: "../scenes"
actors:  [ ... ]            # same actor grammar; x/y/scale are canvas fractions
pixel:   [ ... ]
bubbles: [ ... ]
```

### bubble

```yaml
- text: "Ahoj!"
  kind: speech      # speech | thought | shout
  speaker: tom      # OPTIONAL: auto-place above this actor + aim the tail at
                    #           their head. Prefer this over manual x/y/to.
  x: 0.5            # OPTIONAL bubble centre (panel fraction); else from speaker
  y: 0.18           # OPTIONAL; omit and bubbles stack downward without overlap
  to: [0.4, 0.5]    # OPTIONAL tail target (panel fraction); else speaker's head
  max_chars: 22     # wrap width (optional)
  fs: 16            # font size px (optional)
```

`thought` draws an ellipse with a trail of dots; `shout` draws a spiky burst.
The tail is a slim line dropping from the bubble underside; its tip is capped
short so it never overlaps the figure.

### pixel art

```yaml
# From the library (needs pixel_dir: in the spec):
- art: heart        # library sprites: heart, sun, star, bone
  x: 0.8  y: 0.25  scale: 0.18

# Inline (no pixel_dir needed):
- grid: ["....", ".RR.", ".RR.", "...."]
  palette: {R: "#e8556d"}
  x: 0.5  y: 0.5  scale: 0.3
```

Library sprites live in `<project>/pixel/<name>.yaml`. Inline sprites work with
no `pixel_dir:` at all.

## Adding a character (no code)

A character is an **identity** that owns one or more **poses** (different bodies:
sit, walk, …). Expressions (`face`, …) are authored once and *shared* across
poses. There are two on-disk shapes — use the simpler one until you need poses.

### Single-pose (flat) — the simple case

Create `<project>/characters/<name>/`:

- `base.svg` — the body, drawn in a local `viewBox` (e.g. `0 0 200 320`).
- `<slot>-<variant>.svg` — overlays in the **same** viewBox/coords
  (e.g. `face-happy.svg`, `arms-wave.svg`). They stack on top of the base.
- `character.yaml`:
  ```yaml
  name: <name>
  label: <Display Name>
  viewbox: [200, 320]
  default: {face: neutral, arms: down}
  slots:   {arms: [down, wave, point], face: [neutral, happy, surprised, sad]}
  ```

### Multiple poses

When the **body** changes between poses (legs differ sit vs walk), give each pose
its own `base.svg`. Shared overlays (faces) live at the character root and are
re-registered onto each pose via an **anchor** — a reference point (typically the
head centre) the faces are drawn around.

```
<project>/characters/bara/
  character.yaml          # identity + SHARED slots + default + pose list
  face-happy.svg          # SHARED overlays, drawn around the canonical anchor
  face-neutral.svg
  poses/
    sit/  { pose.yaml, base.svg, [<slot>-<variant>.svg …] }
    walk/ { pose.yaml, base.svg, [<slot>-<variant>.svg …] }
```

```yaml
# character.yaml
name: bara
label: Bára
anchor: [120, 72]                 # canonical point the shared faces are drawn around
slots:  {face: [neutral, happy]}  # SHARED across poses, re-anchored per pose
default: {pose: sit, face: neutral}
poses: [sit, walk]
```

```yaml
# poses/walk/pose.yaml
viewbox: [240, 180]
anchor: [132, 64]                 # where THIS pose's head-centre lands
slots:  {arms: [trot]}            # OPTIONAL pose-specific slots + overlays
default: {arms: trot}
```

The engine shifts each shared overlay by `pose.anchor - character.anchor`, so one
`face-happy.svg` lands correctly on every pose. **Translate-only**: keep the head
the same *size* across poses — only its position changes. To add a pose, drop in a
new `poses/<name>/` (its own `base.svg` + `pose.yaml`) and list it under `poses:`.

> Tip: the seed art is hand/LLM-authored clean SVG, edited directly in the project.
> A visual model is useful as *inspiration* for a character or scene — generate a
> reference image for ideas, then author the crisp SVG by hand. Don't auto-vectorize:
> it breaks overlay/anchor registration and the editable slot structure.
> Use `comicforge inspire` (below) to paint those references.

## Generating reference images (`comicforge inspire`)

Blend a project-wide **theme** (style, color scale, mood) with per-item
**descriptions** and let an image model paint reference art to author SVG from.
The output is inspiration only — it is *not* a shipped asset, and you should not
auto-vectorize it.

1. `<project>/theme.yaml` — the central theme applied to every image:
   ```yaml
   style: >                       # the look, in words
     Hand-drawn children's-book comic. Bold black ink outlines, flat cheerful fills.
   palette: ["#f4d35e", "#ee964b", "#0d3b66"]   # color scale fed to the model
   mood: warm, playful, gentle
   negative: No text, no letters, no words.     # what to avoid (has a default)
   aspect_ratio: "1:1"
   # model: google/imagen-3                     # optional Replicate model override
   ```
2. `<project>/references.yaml` — the things to depict (id → filename):
   ```yaml
   items:
     - {id: tom,  prompt: "A cheerful boy in a striped shirt, full body, neutral pose"}
     - {id: dvur, prompt: "A sunny Czech farmyard with a wooden fence and chicken coop"}
   ```
3. Generate (writes `<project>/references/<id>.png` + `<id>.prompt.txt`):
   ```bash
   comicforge inspire <project>/references.yaml --review        # + a review.html grid
   comicforge inspire <project>/references.yaml --dry-run       # compose prompts, no API call
   comicforge inspire <project>/references.yaml --only tom,dvur --force
   ```

`theme.yaml` and the output `references/` dir default to siblings of the spec
(override with `--theme` / `-o`). Live generation needs the optional extra
(`pip install "comicforge[inspire]"`) and a `REPLICATE_API_TOKEN` (env var or a
`.env` beside the spec). `--dry-run` needs neither — use it to iterate on prompts.

## Adding a scene (no code)

Create a scene directory (e.g. `<project>/scenes/<name>/`) exactly like a character
but with `scene.yaml` instead of `character.yaml`. `base.svg` is the full
background (drawn in its own viewBox); optional `<slot>-<variant>.svg` overlays
add weather/props. The scene is scaled to cover whatever panel (or canvas) it is
placed in.

```
<project>/scenes/<name>/
  base.svg
  <slot>-<variant>.svg   (optional, one per variant)
  scene.yaml
```

Then point your spec at that directory via `scenes_dir:`.

## Adding a pixel-art sprite

Create `<project>/pixel/<name>.yaml`:

```yaml
palette:
  R: "#e8556d"
grid:
  - ".RR."
  - "RRRR"
  - ".RR."
```

Then reference it with `{art: <name>}` in any panel whose spec has `pixel_dir:`
pointing at that `pixel/` directory.

## Notes / limits (v0.1)

- Poses are pre-drawn bodies (a `base.svg` each), not an articulated skeleton;
  shared expressions re-anchor onto them by translation only (no per-pose resize).
- One title strip; panels are a row/column grid (no free-form panel polygons yet).
- Text wrap is a width estimate — check long lines in the render.
- PDF is true vector (crisp at print); PNG is rasterized at `px_per_mm`.
