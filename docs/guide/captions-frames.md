# Captions and frames

Two panel-level touches that do most of the work of making a page look like a
comic rather than a grid of pictures: the narrator's voice, and the line around
the art.

## Captions

A caption is **narration** — the storyteller, not a character. It is drawn as a
flat band along the bottom of the panel, inside the frame, separated from the
art by a hairline in the frame colour.

=== "Render"

    <figure class="cf-demo" markdown>
    ![Two panels with narration bands under the art](../assets/renders/captions.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/captions.yaml"
    ```

```yaml
caption: "Later that afternoon, the yard went quiet."
caption: {text: "Nobody had seen the chickens since lunch.", max_chars: 26}
```

### The art box shrinks

This is the part worth internalising: **the band takes its height off the
picture, not out of it**. The art box becomes shorter, and every panel fraction
inside — actor `x`/`y`/`scale`, bubble placement, sprite positions — stays
relative to the picture.

So adding a caption to a finished panel does not move the composition around; it
squeezes it slightly. Nothing needs re-tuning.

The band's height depends on how many lines the text wraps to, which depends on
`max_chars` and `font_size`. To size a row around one, ask:

```python
from comicforge import caption
caption.height("Later that afternoon, the yard went quiet.", {"font_size": 13})
```

!!! warning "Actors draw over the band"

    The band is painted early, before the figures, so an actor placed low enough
    still covers it. If feet land on your narration, raise the actor's `y` or
    reduce `scale`.

### `caption_style`

Set page-wide at the top level; a panel's `caption: {…}` mapping can override
`text` and `max_chars` per panel.

| Key | Default | Meaning |
|---|---|---|
| `font` | DejaVu Sans stack | Font family |
| `font_size` | `13` | Text size in px |
| `ink` | `#21304a` | Text colour |
| `bg` | `#ffffff` | Band colour |
| `pad` | `8` | Text inset from the band edge |
| `max_chars` | `60` | Wrap width in characters |
| `align` | `left` | `left` or `center` |
| `rule` | `true` | Hairline between art and band |
| `uppercase` | `false` | Render caption text in caps |

```yaml
caption_style:
  font_size: 11
  align: center
  uppercase: true
  bg: "#f4efe2"
```

The hairline is drawn in the frame's colour at the frame's width, so it stays
consistent with the outline — and disappears along with it when the frame width
is `0`.

## Frames

`frame:` is the panel outline. Set it page-wide at the top level; any panel can
override it.

=== "Render"

    <figure class="cf-demo" markdown>
    ![Three panels: page-default frame, no frame, and a heavy round red frame](../assets/renders/frames.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/frames.yaml"
    ```

| Key | Default | Meaning |
|---|---|---|
| `width` | `3.5` | Stroke width in px. `0` draws no outline |
| `color` | `#21304a` | Stroke colour |
| `radius` | `10` | Corner radius — **also clips the art** |

Two things follow from `radius` doubling as a clip:

- Panel contents are cut to the rounded rectangle whether or not the outline is
  drawn. Setting `width: 0` removes the line but keeps the rounded corners.
- For hard corners, set `radius: 0`.

The outline is stroked **last**, over the clipped contents, so it stays crisp:
a figure that overflows the panel is cut off cleanly at the line rather than
straddling it.

### Panel backgrounds

`bg` on a panel is the flat colour behind everything else. The default is a warm
off-white (`#fbfaf6`) that reads as paper rather than screen.

```yaml
panels:
  - bg: "#eef4fb"          # a cool panel for a flashback
  - bg: "#fdf6e3"          # a warm one for the present
```

Under a full-bleed `scene:` or `image:` the background never shows — except with
`fit: contain`, where it fills the letterbox strips.

## Putting it together

A page-wide look, set once at the top:

```yaml
frame:
  width: 3
  color: "#21304a"
  radius: 8
caption_style:
  font_size: 11
  max_chars: 42
bubble_style:
  font_size: 13
  uppercase: true
```

…and one panel that breaks out of it:

```yaml
- frame: {width: 0}        # a borderless establishing shot
  bg: "#0d1b2a"
  caption: {text: "Night.", max_chars: 12}
```
