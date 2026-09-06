# Troubleshooting

## Start here

```bash
cmf validate pages/strip.yaml
```

Most spec problems are one line of output away. `validate` reports **every**
problem at once and, crucially, catches the class of mistake that `render`
ignores in silence: keys it does not recognise. A page that renders "fine" but
looks wrong is very often a typo `render` shrugged at.

---

## Installation

### `no library called "cairo-2" was found`

`cairosvg` loads Cairo at runtime and it is not a pip dependency. Install the
system library — see [Install › Requirements](../install.md#requirements).

### `cmf: command not found`

The tool installed but its bin directory is not on your `PATH`. With uv, that is
`~/.local/bin`. `uv tool update-shell` fixes the shell config; a new shell picks
it up.

---

## Assets

### `library directory is required but was not provided`

Every page spec needs a `library:`, even one pointing at an empty `characters/`
directory. The engine ships no art and will not guess.

```yaml
library: "../characters"
```

Or pass `--library characters` on the command line.

### `character 'tomm' not found in characters. Have: ['bara', 'tom']`

The name in the spec is not a directory in the library. The **directory name**
is what you reference, and `character.yaml`'s `name:` must match it.

### `scene 'x' not found in …`

Either the directory is not there, or it has no `scene.yaml`. A directory
without a manifest is invisible to the library.

### `pixel art 'heart' requires a pixel library`

You wrote `{art: heart}` but no `pixel_dir:` is set. Add the key, or write the
sprite inline as `{grid, palette}` — inline needs no library.

### `tom has no slot 'fcae' (ignored when rendering)`

A typo. This one *renders* — you get the default face and no error — which is
why `validate` exists. The same applies to `post:` for `pose:` and `imge:` for
`image:`.

### `slot 'face' has no variant 'grin'`

Either the variant is missing from `slots:` in the manifest, or the file is not
named `face-grin.svg`. Both have to be true. Check against:

```bash
cmf characters --library characters
```

---

## Drawing

### `… is not a well-formed <svg>…</svg> file`

The engine strips each file to the markup inside its outer `<svg>` element. A
fragment with no `<svg>` wrapper, or a file that is not SVG at all, fails here.

### An overlay lands in the wrong place

Its `viewBox` does not match the base's. Every file in a flat character — and
every file within one pose — must declare the *same* `viewBox`.

### A shared face is offset on one pose only

That pose's `anchor:` is wrong. It should be the point in *that pose's* viewBox
where the head centre lands; the character's `anchor:` is the same point in the
coordinates the shared overlays were drawn in.

### A shared face is the wrong *size* on one pose

Anchors translate; they do not scale. Keep the head the same size across every
pose and move only its position.

### A double outline around the head

The overlay is redrawing part of the base. An expression file should contain
eyes and a mouth, not a head.

---

## Layout

### A figure is cut off at the panel edge

`scale` is the actor's **height** as a fraction of the panel height; the width
follows from the pose's aspect ratio. A wide pose can therefore overflow
sideways while fitting vertically. Lower `scale`, or give the panel more
`width`.

### Feet are drawn over the caption band

The band is painted before the figures, so an actor placed low enough covers it.
Raise `y` or reduce `scale`.

### The interesting part of a scene is cropped away

Scenes are cover-scaled — enlarged to fill the panel in both directions, with
the overflow clipped. Which edge is lost depends on the panel's aspect ratio.
Compose toward the centre, or give the panel a shape closer to the scene's
viewBox.

### The bottom of the page is blank

Every row has a `height_mm` and they do not add up to the page. Give at least
one row a weighted `height:` so it absorbs the remainder.

### Bubbles overlap

Only if you positioned them by hand. Remove `y` (and `x`) and they stack by
measured height without overlapping; use `at:` to move them into corners.

### Text runs past its bubble outline

The width is estimated from per-glyph advance tables, not real font metrics. Set
`max_chars` lower, or `em` below `1.0` for a font narrower than the default.

---

## Rendering

### `this is a 'scene' spec … render it with 'comicforge scene'`

Exactly what it says. `render` draws page specs, `scene` draws standalone
illustrations. Declare `type:` on every spec and the error tells you which is
which.

### The PNG is blurry, or too small

`px_per_mm` is the raster scale — raise it. It does nothing for a PDF, which is
true vector and crisp at any size.

### The SVG or PDF is enormous

A raster `image:` is embedded as base64, so the output carries every image's
full bytes. Downsample the sources to roughly their printed size.

### A change to my art did not show up

Libraries cache per process. That never matters for the CLI, which is a fresh
process each time — but a long-lived script or server holds the loaded
character. Build a new `Library` to pick up edits.

---

## Still stuck

Print what the engine actually sees, rather than what you think it sees:

```bash
cmf characters --library characters      # the character contract
cmf scenes --scenes scenes               # the scene contract
cmf validate pages/strip.yaml            # every problem in the spec
cmf character bara walk happy --library characters   # one figure, alone
cmf panel pages/strip.yaml --row 0 --col 1           # one panel, alone
```

Those five commands answer nearly every "why does it look like that" question.
