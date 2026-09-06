# Bubbles

A bubble is dialogue: an outline, word-wrapped text, and a tail pointing at
whoever is talking. Bubbles are drawn last, on top of everything else in the
panel.

```yaml
bubbles:
  - text: "Ahoj!"
    kind: speech       # speech (default) | thought | shout
    speaker: tom       # place it above this actor and aim the tail at their head
```

Almost always, that is all you write. Coordinates are optional and usually
unnecessary.

## The three kinds

=== "Render"

    <figure class="cf-demo" markdown>
    ![Three panels: a speech bubble, a thought bubble, a shout burst](../assets/renders/bubbles.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/bubbles.yaml"
    ```

| `kind` | Drawn as |
|---|---|
| `speech` | A rounded rectangle with a slim tail (the default) |
| `thought` | An ellipse with a trail of shrinking dots |
| `shout` | A spiky burst |

The tail drops from the bubble's underside toward its target, and its tip is cut
short so it never lands on the figure's face.

## Placing a bubble

Four things can decide where a bubble goes. In order of precedence:

1. **`x` / `y`** — explicit panel fractions for its centre.
2. **`at`** — a corner or edge to hug.
3. **`speaker`** — line it up over that actor.
4. **Nothing** — centred horizontally, stacked from the top.

### `speaker:` — the usual case

`speaker: tom` finds the first actor in the panel whose `char` is `tom`, aligns
the bubble to that actor's `x`, and aims the tail at the actor's head — computed
from their `y` and `scale`, so it keeps pointing at the right place when you
move or resize them.

```yaml
actors:  [{char: tom, face: happy, x: 0.35, y: 0.7, scale: 0.8}]
bubbles: [{text: "Ahoj!", speaker: tom}]
```

A `speaker` naming no actor in the panel is caught by `cmf validate`.

### Stacking — no coordinates at all

A bubble with no `y` is placed below the measured bottom of the bubbles already
drawn, starting near the panel top. Because it is *measured*, not guessed, the
stack never overlaps however long the lines run.

=== "Render"

    <figure class="cf-demo" markdown>
    ![Three bubbles of different lengths stacked down a panel without overlapping](../assets/renders/bubble-stack.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/bubble-stack.yaml"
    ```

A bubble with no `x` is centred — or aligned to its speaker, if it has one. So a
panel with no actors at all, like a
[raster-backed panel](images.md), can carry its dialogue in order and omit every
coordinate.

Whatever the placement, every bubble is finally nudged to stay inside the panel.
One too wide or too tall to fit is centred instead.

### `at:` — hugging a corner

=== "Render"

    <figure class="cf-demo" markdown>
    ![A panel with bubbles at all nine anchor positions](../assets/renders/bubble-at.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/bubble-at.yaml"
    ```

The nine anchors are three columns (`l`, `c`, `r`) crossed with three edges
(`t`, `c`, `b`):

| | left | centre | right |
|---|---|---|---|
| **top** | `tl` | `t` | `tr` |
| **middle** | `l` | `c` | `r` |
| **bottom** | `bl` | `b` | `br` |

Each column keeps its own top and bottom stack, and a bubble only moves past the
ones it would actually overlap. So `tl` and `tr` sit side by side when there is
room, and `bl` climbs upward from the bottom edge. `c` is the exception: it
centres and does not stack.

`at:` is the tool of choice over busy art — put the dialogue in the corners and
keep it off the faces.

### `to:` — aiming the tail by hand

```yaml
- text: "Odsud!"
  to: [0.4, 0.55]     # panel fractions
```

Use `to` when the tail should point at something that is not an actor — an
off-panel voice, a radio, a hole in the ground. With a `speaker` and no `to`,
the head position is worked out for you.

## Text and wrapping

| Key | Default | Meaning |
|---|---|---|
| `text` | required | The line. Required — `validate` flags a bubble without it |
| `max_chars` | `22` | Wrap width, in characters |
| `fs` | from `bubble_style` | Font size in px for this bubble |
| `uppercase` | from `bubble_style` | Force this bubble's text to caps |

Wrapping breaks on spaces at `max_chars`, and the outline is sized from an
*estimate* of the rendered width — capitals are measured wider than lowercase,
which is why `uppercase` is safe to use. It is still an estimate: check long
lines in the render, and reach for `max_chars` or `em` when a line crowds its
outline.

## Page-wide lettering

`bubble_style` at the top level of the spec sets the look of every bubble on the
page. Per-bubble keys still win.

=== "Render"

    <figure class="cf-demo" markdown>
    ![Two panels: one bubble in the page's caps style, one overriding it](../assets/renders/lettering.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/lettering.yaml"
    ```

| Key | Default | Meaning |
|---|---|---|
| `font` | DejaVu Sans stack | Font family |
| `font_size` | `16` | Text size in px |
| `pad` | `14` | Inset from text to outline |
| `radius` | `18` | Speech-bubble corner radius (capped at half the height) |
| `stroke` | `#21304a` | Outline colour |
| `stroke_width` | `3` | Outline weight |
| `fill` | `#ffffff` | Bubble interior |
| `ink` | `#21304a` | Text colour |
| `uppercase` | `false` | Render all bubble text in caps |
| `em` | `1.0` | Width scale of the text measure |

`uppercase: true` is classic comic lettering, and it costs nothing — the
measurement accounts for the wider glyphs.

`em` is the escape hatch for a font whose glyphs are narrower than the default
measure assumes: set `em: 0.8` for a narrow handwriting face and the outlines
hug the words instead of floating around them.

## Common shapes

```yaml
# a two-hander: each bubble anchored to its own speaker
actors:
  - {char: tom,  face: angry, arms: hips, x: 0.28, y: 0.68, scale: 0.8}
  - {char: bara, pose: sit, face: sad,    x: 0.74, y: 0.78, scale: 0.45}
bubbles:
  - {text: "Kdo to snědl?", kind: shout,  speaker: tom, at: tl}
  - {text: "Já ne…",        kind: speech, speaker: bara, at: br}

# an internal monologue over a full-bleed background, no actors needed
bubbles:
  - {text: "Byla to dlouhá cesta.", kind: thought, at: tl, max_chars: 18}

# an off-panel voice
bubbles:
  - {text: "Večeře!", kind: speech, at: tr, to: [1.0, 0.5]}
```
