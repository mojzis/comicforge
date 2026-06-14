# ComicForge — agent guide

You write a **comic page as a YAML spec**; the engine renders it to SVG/PNG/PDF.
This file is the full authoring contract. For deeper explanations (path resolution,
how to add characters/scenes, pixel-art format) see
[`docs/authoring-guide.md`](docs/authoring-guide.md).

## Loop

1. Read the libraries:
   - `uv run --active comicforge characters --library library/characters` → JSON of
     every character, its **slots**, **variants** per slot, and the defaults.
   - `uv run --active comicforge scenes --scenes projects/_scenes` → JSON of every
     scene background and its slots.
2. Write a spec (see grammar below). Spec-level keys declare where assets live:
   ```yaml
   library:    "../../library/characters"
   scenes_dir: "../../projects/_scenes"
   pixel_dir:  "../../library/pixel"
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
library:    "../../library/characters"   # path to character library dir
scenes_dir: "../../projects/_scenes"     # path to scenes dir (omit if no scenes used)
pixel_dir:  "../../library/pixel"        # path to pixel-art library dir (omit if inline only)

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
  face: happy       # any slot -> a valid variant; omitted slots use defaults
  arms: wave
  x: 0.35           # centre (panel fraction)
  y: 0.62
  scale: 0.85       # height as fraction of panel height
  flip: false       # mirror horizontally (face the other way)
```

Slots are per character. `tom` has `face`
(neutral/happy/surprised/sad/angry/laugh/wink) and `arms`
(down/wave/point/crossed/hips/thumbsup); `bara` has `face` (neutral/happy).
Always confirm against `comicforge characters --library library/characters` —
never guess a variant that isn't listed.

### scene (panel background)

A scene is a reusable illustrated background, scaled to *cover* the panel.

```yaml
scene: dvur                 # just the name…
scene: {name: dvur, weather: rain}   # …or pick scene slot variants
```

Confirm scenes/slots with `comicforge scenes --scenes projects/_scenes`.
Seeds: `dvur` (farmyard, slot `weather: clear|rain`), `pokoj` (room, no slots).
Both live in `projects/_scenes/`.

## Standalone illustration (no comic grid)

Render one scene filling the whole canvas with actors/bubbles on top — good for
covers and single panels. Render with `comicforge scene file.yaml -o out.png`:

```yaml
title: "Optional"
scene: {name: dvur, weather: clear}
scale: 3                    # px per scene unit (canvas = scene viewbox × scale)
library:    "../../library/characters"
scenes_dir: "../../projects/_scenes"
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

Library sprites live in `library/pixel/<name>.yaml`. Inline sprites work with
no `pixel_dir:` at all.

## Adding a character (no code)

Create `library/characters/<name>/`:

- `base.svg` — the body, drawn in a local `viewBox` (e.g. `0 0 200 320`).
- `<slot>-<variant>.svg` — overlays drawn in the **same** viewBox/coords
  (e.g. `face-happy.svg`, `arms-wave.svg`). They stack on top of the base.
- `character.yaml`:
  ```yaml
  name: <name>
  label: <Display Name>
  viewbox: [200, 320]
  default: {face: neutral, arms: down}
  slots:   {arms: [down, wave, point], face: [neutral, happy, surprised, sad]}
  ```

All variants share the base canvas, so "posing" = swapping which overlays stack.
For a brand-new pose, add one overlay SVG and list it under `slots`.

> Tip: the seed art is hand/LLM-authored clean SVG (see `tools/make_assets.py`).
> A visual model is useful as *inspiration* for a character or scene — generate a
> reference image for ideas, then author the crisp SVG by hand. Don't auto-vectorize:
> it breaks overlay registration and the editable slot structure.

## Adding a scene (no code)

Create a scene directory (e.g. `projects/_scenes/<name>/`) exactly like a character
but with `scene.yaml` instead of `character.yaml`. `base.svg` is the full
background (drawn in its own viewBox); optional `<slot>-<variant>.svg` overlays
add weather/props. The scene is scaled to cover whatever panel (or canvas) it is
placed in.

```
projects/_scenes/<name>/
  base.svg
  <slot>-<variant>.svg   (optional, one per variant)
  scene.yaml
```

Then point your spec at that directory via `scenes_dir:`. Scenes are project
content — they live under `projects/`, not under `library/`.

## Adding a pixel-art sprite to the library

Create `library/pixel/<name>.yaml`:

```yaml
palette:
  R: "#e8556d"
grid:
  - ".RR."
  - "RRRR"
  - ".RR."
```

Then reference it with `{art: <name>}` in any panel that has `pixel_dir:` pointing
at `library/pixel`.

## Notes / limits (v0.1)

- "Poses" are pre-drawn overlay presets, not an articulated skeleton.
- One title strip; panels are a row/column grid (no free-form panel polygons yet).
- Text wrap is a width estimate — check long lines in the render.
- PDF is true vector (crisp at print); PNG is rasterized at `px_per_mm`.
