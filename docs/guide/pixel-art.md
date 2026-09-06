# Pixel art

A sprite is a grid of characters and a palette that maps each character to a
colour. It is the cheapest way to get a prop, an icon or an emotive symbol into
a panel — a heart, a bone, a star over someone's head — without opening a vector
editor.

```yaml
pixel:
  - art: heart        # from the project's pixel/ directory
    x: 0.8
    y: 0.25
    scale: 0.18
```

=== "Render"

    <figure class="cf-demo" markdown>
    ![Two panels: a heart and a sun from the library, and an inline sprite](../assets/renders/pixel.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/pixel.yaml"
    ```

Sprites are drawn after the background and **before** the actors, so a figure
placed over one covers it.

## The two forms

### From the library

```yaml
pixel_dir: "../pixel"      # needed for `art:` references

pixel:
  - {art: heart, x: 0.8, y: 0.25, scale: 0.18}
```

Library sprites live one file per sprite at `<project>/pixel/<name>.yaml`:

```yaml title="pixel/heart.yaml"
--8<-- "demos/tutorial-art/pixel/heart.yaml"
```

Ask a project what it has the same way you ask about characters — the file names
are the sprite names:

```bash
ls pixel/
```

A name that is not there fails with the available list, and `cmf validate`
catches it before you render.

### Inline

```yaml
pixel:
  - grid: ["....", ".RR.", ".RR.", "...."]
    palette: {R: "#e8556d"}
    x: 0.5
    y: 0.5
    scale: 0.3
```

Inline sprites need no `pixel_dir:` at all. Use them for something that appears
once; promote it to a file the second time you need it.

## Writing a grid

- `grid` is a list of strings, one per row. Rows should be the same length —
  the sprite's width is taken from the longest.
- `.` and a space are **transparent**. Every other character is looked up in
  `palette`; a character with no entry falls back to black.
- Palette keys are case-sensitive, which gives you cheap shading: `R` for the
  body colour and `r` for its shadow.

```yaml
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

Sprites are rendered with `shape-rendering="crispEdges"`, so the cells stay hard
at any scale — no blurring in a PNG, no seams in a PDF.

## Placement

| Key | Default | Meaning |
|---|---|---|
| `x` | `0.5` | Horizontal centre, fraction of panel width |
| `y` | `0.5` | Vertical centre, fraction of panel height |
| `scale` | `0.2` | **Height**, as a fraction of panel height |

Width follows from the grid's aspect ratio, so a wide sprite at `scale: 0.2` is
wider than a square one. A panel can hold as many sprites as you like; they are
drawn in list order.

## What they are good for

Pixel sprites are deliberately crude, which is exactly why they read as symbols
rather than as objects in the scene:

```yaml
# emotional punctuation over a character's head
pixel: [{art: heart, x: 0.72, y: 0.22, scale: 0.16}]

# a prop the story is about
pixel: [{art: bone,  x: 0.2,  y: 0.6,  scale: 0.18}]

# weather or time of day, cheaply
pixel: [{art: sun,   x: 0.85, y: 0.15, scale: 0.2}]
```

For anything that needs to be *drawn* rather than *indicated*, use a scene
overlay or a character slot instead.
