# Pages, rows and panels

A page spec is a page-level block of settings followed by `rows:`. Each row is a
list of `panels:`, laid out left to right. That is the whole layout model —
there are no nested grids and no free-form panel shapes.

```yaml
title: "Optional page title"
page: A4
library: "../characters"

rows:
  - panels: [ … ]      # first row, top of the page
  - panels: [ … ]      # second row, below it
```

## The page

| Key | Default | Meaning |
|---|---|---|
| `page` | `A4` | `A4`, `A5`, `letter`, or `[width_mm, height_mm]` |
| `bg` | `#ffffff` | Paper colour, behind everything |
| `px_per_mm` | `4` | Raster scale. Only affects `.png` output |
| `margin_mm` | `12` | White border around the whole grid |
| `gutter_mm` | `5` | Gap between panels, and between rows |
| `title` | — | A bold caption strip across the top |
| `title_style` | — | `{font_size, color, font}` |

Millimetres are the one unit in the spec, and they only appear here — paper is
physical, so page geometry is too. Everything *inside* a panel is a fraction.

```yaml
page: A4                # 210 × 297 mm
page: [190, 95]         # a custom landscape strip
px_per_mm: 6            # a PNG at 1140 × 570
```

`px_per_mm` is a raster knob only. A `.pdf` is true vector and ignores it
entirely; raise it when you want a bigger PNG, not when you want better print
quality.

!!! note "Where a title eats space"

    A `title:` takes its font size plus 14 px off the top of the grid, so the
    panels start lower. It is one strip for the whole page — there is no
    per-row heading.

## Rows

Rows divide the vertical space left after margins, the title and the gutters.

```yaml
rows:
  - height: 2          # this row is twice as tall as…
    panels: [ … ]
  - height: 1          # …this one
    panels: [ … ]
```

`height` is a **relative weight**, not a unit. Omit it and it is `1`, so a page
of plain rows splits the height evenly.

For a row that must be a specific size, use `height_mm` instead:

```yaml
rows:
  - height_mm: 40      # exactly 40 mm tall
    panels: [ … ]
  - height: 1          # …and the weighted rows share whatever is left
    panels: [ … ]
```

Fixed rows are measured out first; the weighted rows divide the remainder. If
*every* row is fixed and they do not add up to the page, the leftover space at
the bottom simply stays blank.

## Panels

Inside a row, `width` works exactly like `height` does for rows — a relative
weight sharing the row's width after gutters.

=== "Render"

    <figure class="cf-demo" markdown>
    ![Two rows: a wide panel beside a narrow one, then three equal panels](../assets/renders/grid.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/grid.yaml"
    ```

The first row's panels are weighted `2` and `1`, so they take two thirds and one
third of the width. The second row's three panels have no `width` at all, so
they are equal. Vertically, the first row's `height: 2` against the second's
`height: 1` splits the grid two-to-one.

### Panel keys

| Key | Meaning |
|---|---|
| `width` | Relative width weight inside the row (default `1`) |
| `bg` | Flat background colour (default `#fbfaf6`, a warm off-white) |
| `frame` | Outline override for this panel — see [Captions and frames](captions-frames.md) |
| `caption` | Narration band under the art, inside the frame |
| `scene` | A [scene background](scenes.md) |
| `image` | A [raster background](images.md) |
| `actors` | [Characters](actors.md) placed in the panel |
| `pixel` | [Pixel-art sprites](pixel-art.md) |
| `bubbles` | [Speech, thought and shout bubbles](bubbles.md) |

Any other key in a panel is a typo, and
[`cmf validate`](../reference/cli.md#validate) says so. The renderer will not —
it ignores what it does not recognise, so `imge:` costs you a background and no
error message.

## Panel contents are fractional

Every coordinate inside a panel is a fraction of *that panel*: `x` from left to
right, `y` from top to bottom, and `scale` as a fraction of the panel's height.

That means panel contents survive layout changes. Re-weight a row, switch from
A4 to a landscape strip, add a caption band that shrinks the art box — the
figures stay in the same relative composition. Nothing has to be recomputed.

## Looking at one panel

Once a page is full, re-rendering all of it to check one corner is a waste.
Render the panel instead:

```bash
cmf panel pages/strip.yaml --row 0 --col 1        # 0-indexed, row then column
cmf panel pages/strip.yaml --all -o panels/       # every panel into a directory
cmf panel pages/strip.yaml --row 1 --col 0 --scale 1.0
```

<figure class="cf-demo" markdown>
![A single panel from the kosticka demo page, rendered on its own](../assets/renders/kosticka-r0c1.png)
<figcaption><code>cmf panel examples/pes/pages/kosticka.yaml --row 0 --col 1</code></figcaption>
</figure>

`--scale` defaults to `0.5`, which is deliberately low-resolution: the point is
a quick look, not a final render. This is the right way to inspect one panel —
rendering the whole page and cropping it with an image tool gives you the same
picture for much more work.

## Output formats

The extension decides the format:

```bash
cmf render pages/strip.yaml -o strip.png    # raster at px_per_mm
cmf render pages/strip.yaml -o strip.pdf    # true vector
cmf render pages/strip.yaml -o strip.svg    # the composed document
```

Omit `-o` entirely and the render lands in `output/` with a timestamp, so
successive attempts accumulate side by side.
