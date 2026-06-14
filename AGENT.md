# ComicForge — agent guide

You write a **comic page as a YAML spec**; the engine renders it to SVG/PNG/PDF.
This file is the full contract. Nothing else is needed to author a page.

## Loop
1. Read the character library: `python -m comicforge characters` → JSON of every
   character, its **slots**, the **variants** per slot, and the defaults.
2. Write a spec (see grammar below).
3. Render: `python -m comicforge render mystrip.yaml -o out.pdf`
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

rows:                             # page is a stack of rows…
  - height: 1.0                   # relative row height (default 1)
    panels:                       # …each row is a left→right list of panels
      - width: 1.0                # relative panel width (default 1)
        bg: "#fbfaf6"             # optional panel background
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
Slots are per character. `tom` has `face` (neutral/happy/surprised/sad) and
`arms` (down/wave/point); `bara` has `face` (neutral/happy). Always confirm
against `comicforge characters` — never guess a variant that isn't listed.

### bubble
```yaml
- text: "Ahoj!"
  kind: speech      # speech | thought | shout
  x: 0.5            # bubble centre (panel fraction)
  y: 0.18
  to: [0.4, 0.5]    # OPTIONAL tail target (panel fraction), usually a mouth
  max_chars: 22     # wrap width (optional)
  fs: 16            # font size px (optional)
```
`thought` draws an ellipse with a trail of dots; `shout` draws a spiky burst.

### pixel art
```yaml
- art: heart        # built-ins: heart, sun, star, bone
  x: 0.8  y: 0.25  scale: 0.18
# …or inline your own:
- grid: ["....", ".RR.", ".RR.", "...."]
  palette: {R: "#e8556d"}
  x: 0.5  y: 0.5  scale: 0.3
```

## Adding a character (no code)
Create `characters/<name>/`:
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

## Notes / limits (v0.1)
- "Poses" are pre-drawn overlay presets, not an articulated skeleton.
- One title strip; panels are a row/column grid (no free-form panel polygons yet).
- Text wrap is a width estimate — check long lines in the render.
- PDF is true vector (crisp at print); PNG is rasterized at `px_per_mm`.
