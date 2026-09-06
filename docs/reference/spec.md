# Spec reference

Every key a spec can hold, with its default. For explanations and pictures, the
[authoring guide](../guide/pages.md) covers the same ground with worked
examples.

Two spec types share most of this grammar:

| `type:` | Rendered by | Shape |
|---|---|---|
| `page` (default) | `cmf render` | A grid of `rows:` and panels on a paper-sized canvas |
| `scene` | `cmf scene` | One background filling the canvas, no grid |

`type:` is inferred when omitted — a top-level background with no `rows:` is
taken to be a scene — but declaring it turns a confusing crash into a clear
message, and lets `validate` check that the type matches the structure.

## Page-level keys

| Key | Default | Meaning |
|---|---|---|
| `type` | inferred | `page` or `scene` |
| `title` | — | Bold caption strip across the top of the page |
| `title_style` | see below | `{font_size, color, font}` |
| `page` | `A4` | `A4`, `A5`, `letter`, or `[width_mm, height_mm]` |
| `bg` | `#ffffff` | Paper colour |
| `px_per_mm` | `4` | Raster scale. PNG only — PDF is vector |
| `margin_mm` | `12` | Border around the whole grid |
| `gutter_mm` | `5` | Gap between panels and between rows |
| `frame` | see below | Panel outline, page-wide |
| `bubble_style` | see below | Bubble look, page-wide |
| `caption_style` | see below | Caption look, page-wide |
| `library` | — | Character directory. **Required** for any page |
| `scenes_dir` | — | Scene directory. Needed only if a `scene:` is used |
| `pixel_dir` | — | Sprite directory. Needed only for `{art: …}` references |
| `rows` | — | The grid. Required on a page spec |

Page sizes in millimetres: `A4` is 210 × 297, `A5` is 148 × 210, `letter` is
216 × 279.

```yaml
title_style: {font_size: 26, color: "#21304a", font: "DejaVu Sans, …"}
```

A title takes its font size plus 14 px off the top of the grid. On a *scene*
spec there is no strip — the title is drawn over the art at 22 px by default.

## Rows

| Key | Default | Meaning |
|---|---|---|
| `height` | `1` | Relative weight for sharing the vertical space |
| `height_mm` | — | Fixed height instead of a weight |
| `panels` | — | Left-to-right list of panels. Required |

Fixed rows are measured first; weighted rows divide what is left. If every row is
fixed and they do not fill the page, the remainder stays blank.

## Panels

| Key | Default | Meaning |
|---|---|---|
| `width` | `1` | Relative weight for sharing the row's width |
| `bg` | `#fbfaf6` | Flat background colour |
| `frame` | inherits page | Outline override for this panel |
| `caption` | — | Narration band: a string, or `{text, max_chars}` |
| `scene` | — | Scene background |
| `image` | — | Raster background |
| `actors` | — | List of characters to place |
| `pixel` | — | List of pixel sprites |
| `bubbles` | — | List of bubbles |

Any other key is a typo. `validate` flags it; `render` ignores it silently.

### Draw order within a panel

`bg` → `caption` band → `image` → `scene` → `pixel` → `actors` (list order) →
`bubbles` → `frame`. Everything but the frame is clipped to the panel's rounded
rectangle.

## `frame`

| Key | Default | Meaning |
|---|---|---|
| `width` | `3.5` | Stroke width in px. `0` = no outline |
| `color` | `#21304a` | Stroke colour |
| `radius` | `10` | Corner radius — **also clips the panel contents** |

Set page-wide, override per panel. `radius` applies to the clip whether or not
the outline is drawn.

## `actors[]`

| Key | Default | Meaning |
|---|---|---|
| `char` | **required** | Character name from the manifest |
| `pose` | character's default | Which pose to draw |
| *any slot name* | slot's default | `face: happy`, `arms: wave`, … |
| `x` | `0.5` | Centre, fraction of panel width |
| `y` | `0.6` | Centre, fraction of panel height |
| `scale` | `0.8` | Height, as a fraction of panel height |
| `flip` | `false` | Mirror horizontally |

Drawn in list order — later actors cover earlier ones.

## `bubbles[]`

| Key | Default | Meaning |
|---|---|---|
| `text` | **required** | The line |
| `kind` | `speech` | `speech`, `thought` or `shout` |
| `speaker` | — | Character name of an actor in this panel: aligns the bubble and aims the tail at their head |
| `at` | — | Corner or edge: `tl` `t` `tr` `l` `c` `r` `bl` `b` `br` |
| `x` | speaker's `x`, else centre | Centre, fraction of panel width |
| `y` | stacked below the previous bubble | Centre, fraction of panel height |
| `to` | speaker's head | Tail target `[x, y]` in panel fractions |
| `max_chars` | `22` | Wrap width in characters |
| `fs` | `bubble_style.font_size` | Font size in px for this bubble |
| `uppercase` | `bubble_style.uppercase` | Force this bubble to caps |

Precedence for placement: explicit `x`/`y` → `at` → `speaker` → stack from the
top. Every bubble is finally clamped to stay inside the panel; one too large to
fit is centred.

`at` columns (`l`/`c`/`r`) each keep their own top and bottom stack, so `tl` and
`tr` sit side by side and `bl` climbs up from the bottom. `c` centres and does
not stack.

## `bubble_style`

Page-wide; every per-bubble key above overrides it.

| Key | Default | Meaning |
|---|---|---|
| `font` | `DejaVu Sans, Helvetica, Arial, sans-serif` | Font family |
| `font_size` | `16` | Text size in px |
| `pad` | `14` | Text inset from the outline |
| `radius` | `18` | Speech-bubble corner radius (capped at half the height) |
| `stroke` | `#21304a` | Outline colour |
| `stroke_width` | `3` | Outline weight |
| `fill` | `#ffffff` | Bubble interior |
| `ink` | `#21304a` | Text colour |
| `uppercase` | `false` | Render all bubble text in caps |
| `em` | `1.0` | Width scale of the text measure — lower for a narrow font |

## `caption` and `caption_style`

```yaml
caption: "Rain came."
caption: {text: "Rain came.", max_chars: 26}
```

| `caption_style` key | Default | Meaning |
|---|---|---|
| `font` | DejaVu Sans stack | Font family |
| `font_size` | `13` | Text size in px |
| `ink` | `#21304a` | Text colour |
| `bg` | `#ffffff` | Band colour |
| `pad` | `8` | Text inset from the band edge |
| `max_chars` | `60` | Wrap width in characters |
| `align` | `left` | `left` or `center` |
| `rule` | `true` | Hairline between art and band, in the frame colour |
| `uppercase` | `false` | Render caption text in caps |

The band takes its height off the art box, so panel fractions stay relative to
the picture. Band height is
`lines × font_size × 1.25 + 2 × pad`; `comicforge.caption.height(text, style)`
computes it for you.

## `scene`

```yaml
scene: dvur                          # short form
scene: {name: dvur, weather: rain}   # pick slot variants
```

Cover-scaled: enlarged until it fills the panel in both directions, centred,
overflow clipped. Requires `scenes_dir:`.

## `image`

```yaml
image: "art/01.png"                    # short form, fit: cover
image: {src: "art/01.png", fit: contain}
```

| Key | Default | Meaning |
|---|---|---|
| `src` | **required** | Path, resolved against the spec file's directory |
| `fit` | `cover` | `cover` (fill + centre-crop) or `contain` (fit inside + letterbox) |

`.png`, `.jpg`/`.jpeg`, `.gif` and `.webp`. Embedded as a base64 `data:` URI, so
`.svg` and `.pdf` output stays self-contained — and carries the image's full
byte weight.

## `pixel[]`

| Key | Default | Meaning |
|---|---|---|
| `art` | — | Sprite name from `pixel_dir` |
| `grid` | — | Inline: list of equal-length strings |
| `palette` | `{}` | Inline: character → hex colour |
| `x` | `0.5` | Centre, fraction of panel width |
| `y` | `0.5` | Centre, fraction of panel height |
| `scale` | `0.2` | Height, as a fraction of panel height |

Give either `art` or `grid` + `palette`. `.` and space are transparent; a
character with no palette entry renders black.

## Scene-spec keys

A `type: scene` spec takes every panel key at the top level, plus:

| Key | Default | Meaning |
|---|---|---|
| `scale` | `4` with `scene:`, `1` with `image:` | Output px per artwork unit |

Canvas size is the scene's viewBox × `scale`, or the image's pixel dimensions ×
`scale`. There is no `page:`, no margin, no gutter and no outline — though the
art is still clipped to the default `frame.radius` of 10 px, so set
`frame: {radius: 0}` for square corners.

## Path resolution

| Where | Resolved against |
|---|---|
| `library:`, `scenes_dir:`, `pixel_dir:`, a panel's `image:` | The **spec file's** directory |
| `--library`, `--scenes`, `--pixel-dir` | Your **current working directory** |

Absolute paths are used as-is. A CLI flag overrides the corresponding spec key
entirely.

This is why a spec in `pages/` writes `library: "../characters"` and works no
matter where you run `cmf` from.

### When a directory is missing

`library:` is required for any page. Leave it out and you get:

```
ValueError: library directory is required but was not provided.
Set 'library:' in the spec or pass the corresponding CLI flag.
```

`scenes_dir:` fails only when a panel actually asks for a scene. `pixel_dir:` is
needed only for `{art: …}` references — inline `{grid, palette}` sprites work
with no library at all.

## A complete page

```yaml
--8<-- "demos/strip.yaml"
```

## A complete illustration

```yaml
--8<-- "demos/illustration.yaml"
```
