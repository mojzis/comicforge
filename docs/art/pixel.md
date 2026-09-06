# Making a pixel sprite

One YAML file. A grid of characters, and a palette that says what each character
means.

```yaml title="pixel/heart.yaml"
palette:
  R: "#e8556d"     # highlight
  r: "#b83e54"     # shadow
grid:
  - ".RR..RR."
  - "RRRRRRRR"
  - "RrrrrrrR"
  - ".RRRRRR."
  - "..RRRR.."
  - "...RR..."
```

Drop it in `<project>/pixel/` and reference it as `{art: heart}` from any spec
whose `pixel_dir:` points there. That is the whole workflow — see
[Pixel art](../guide/pixel-art.md) for placing one in a panel.

## The rules

- **`grid`** is a list of strings, one per row. Keep them the same length; the
  sprite's width is taken from the longest row, so a short row is padded on the
  right with transparency.
- **`.` and space are transparent.** Everything else is a palette lookup.
- **Palette keys are single characters and case-sensitive.** `R` and `r` are
  different colours, which is the cheapest possible shading scheme.
- **A character with no palette entry renders black.** Useful as a deliberate
  outline colour; less useful as a typo.

## Drawing one

Sprites read best small. Sixteen cells across is plenty for a prop; the demo
sprites are seven or eight. Resolution is not what makes them legible — contrast
and silhouette are.

A workable order:

1. Block the silhouette in one colour, on a grid you can see the whole of.
2. Check it at the size it will actually appear (`scale: 0.18` of a panel is
   small). If the shape is not readable there, simplify rather than add detail.
3. Add a second, darker palette entry for the underside or the shadowed edge.
4. Add an outline only if the sprite will sit on a busy background.

```yaml
# a bone: silhouette first, then one shadow tone
palette:
  B: "#f2ece0"
  b: "#cfc5b2"
grid:
  - "BB...BB"
  - "BBBBBBB"
  - "bb...bb"
```

## What they are for

Pixel sprites are intentionally crude. That crudeness is a signal: they read as
**symbols** — a heart of affection, a star of surprise, an object the story is
pointing at — rather than as things physically present in the scene.

Anything that has to look like it belongs in the world should be drawn as a
scene overlay or a character slot instead.

## Inline versus a file

```yaml
# once, in one panel — inline, no pixel_dir needed
pixel:
  - grid: ["....", ".RR.", ".RR.", "...."]
    palette: {R: "#e8556d"}
    x: 0.5
    y: 0.5
    scale: 0.3
```

Inline is right for a one-off. The second time you want the same sprite, move it
to `pixel/<name>.yaml` — then it has a name, it appears everywhere at once when
you edit it, and `cmf validate` can check the reference.

## Rendering

Sprites are emitted as one `<rect>` per opaque cell inside a
`shape-rendering="crispEdges"` group. The cells stay hard at any scale: no
blurring in a PNG, no seams in a PDF, no interpolation ever.

That also means a large sprite is a lot of rectangles. A 64 × 64 grid is four
thousand of them in the output — fine once, heavy on every panel of a long page.
