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
short so it never lands on the figure's face. [`tail:`](#tail-the-tails-look)
picks another look — a curved comic tail, a line all the way, or none — and
[`tail_from`](#tail_from-where-the-tail-leaves) picks where it leaves the bubble.

## Placing a bubble

Four things can decide where a bubble goes. In order of precedence:

1. **`x` / `y`** — explicit panel fractions for its centre.
2. **`at`** — a corner or edge to hug.
3. **`speaker`** — line it up over that actor, or, on a panel with
   [`speakers:`](#speakers-speaker-points-without-actors), place it in
   reading order on that speaker's side.
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

A `speaker` naming neither an actor nor a `speakers:` point in the panel is
caught by `cmf validate`.

### `speakers:` — speaker points without actors

A panel over raster art has no actors for `speaker:` to find. Give the panel
the head of each speaking figure instead, in panel fractions:

```yaml
image: "art/03.png"
speakers:
  ema: [0.72, 0.30]
  jan: [0.25, 0.42]
bubbles:
  - {text: "Kde jsi byl?", speaker: ema}
  - {text: "Venku.",       speaker: jan}
```

`speaker: ema` now resolves to that point: the tail aims there (unless the
bubble has a `to:`). An actor with the same `char` wins over a point of the same
name, so the two can share a panel.

On a panel with `speakers:`, every bubble that has a `speaker` and none of
`x`, `y` or `at` is placed **in reading order**:

- it goes on its speaker's side of the panel — over the speaker, or hugging
  that side's edge;
- its top sits clearly below the previous bubble's top — at least half that
  bubble's height lower — so the panel reads top to bottom, then left to right;
- among the spots that satisfy that, it takes one that keeps clear of every
  speaker point and does not cross an earlier bubble's tail, staying as close
  to its speaker and as high up as it can.

So a right-hand speaker who talks first gets the top right, and the reply goes
lower left.

=== "Render"

    <figure class="cf-demo" markdown>
    ![Four raster panels with bubbles placed from speaker points: reading order, a line tail, a pinned tail start, a dotted thought line](../assets/renders/speakers.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/speakers.yaml"
    ```

Bubbles with `x`/`y` or `at` keep their manual place — and still count as the
"previous bubble" for the next one. Panels without `speakers:` lay out exactly
as before.

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

### `tail_from:` — where the tail leaves

By default the tail leaves the edge facing its target, slid toward the target
but kept within the middle of that edge. `tail_from` overrides either half:

```yaml
- {text: "Kvok!", speaker: hen, at: tl, tail_from: r}                  # right edge, auto spot
- {text: "Kvok!", speaker: hen, at: tl, tail_from: 0.8}                # auto edge, 80% along it
- {text: "Kvok!", speaker: hen, at: tl, tail_from: {edge: r, pos: 0.8}} # both
```

`edge` is `t`, `b`, `l` or `r`; `pos` runs from `0` (left end of a top/bottom
edge, top end of a side) to `1`. Set it on a bubble, or page-wide in
`bubble_style`.

### `tail:` — the tail's look

```yaml
bubble_style: {tail: curve}    # every bubble on the page
# …or per bubble:
- {text: "Mně to nevadí.", speaker: hen, tail: line, tail_bend: -0.5}
```

=== "Render"

    <figure class="cf-demo" markdown>
    ![Four panels: a wedge tail, curved tails bowing apart, bent line tails, a thought trail on a curve and a shout with no tail](../assets/renders/tails.png)
    </figure>

=== "Spec"

    ```yaml
    --8<-- "demos/tails.yaml"
    ```

The look is independent of the bubble `kind`:

| `tail` | Drawn as |
|---|---|
| `wedge` | The default: a slim, straight tail, cut short of the figure |
| `curve` | The classic comic tail: a longer tapered wedge with curved sides, joined to the bubble without a line across its base |
| `line` | A thin ink line from the bubble to just short of the speaker, on a paper-coloured halo so it stays legible over busy art |
| `none` | No tail. The bubble is still placed by its `speaker` |

A `thought` keeps its trail of circles along whatever path the tail takes — three
shrinking circles for `wedge` and `curve`, a dotted trail for `line`.

`tail_bend` bows a `curve` or `line` through one control point: from `-1` to
`1`, `0` straight, positive to the right of the tail's direction as it runs from
bubble to speaker. Leave it unset and the tail bends gently *away* from the
nearest other bubble in the panel — or from the panel centre, when the bubble is
alone — so neighbouring tails part instead of crossing. A `wedge` is always
straight.

`tail_gap` (default `12` px) is how far short of the target a line stops.

## Layout warnings

`cmf validate` lays out every panel's bubbles and warns — without failing —
about things that render but read badly:

- a bubble **out of reading order**: its top above the previous bubble's, or
  level with it but further left;
- two **tails that cross** (the lines from each bubble to its target);
- a bubble **covering a speaker point** — an actor's head or a `speakers:`
  point.

```
pages/strip.yaml: ok, 1 warning(s)
  - warning: r0c1: bubble 1 "Venku." sits above bubble 0 "Kde jsi byl?" but comes after it (out of reading order)
```

Pass `--strict` to make warnings fail the check. The same geometry is
available from Python, without rendering, via
[`bubble_layout`](../reference/python-api.md#bubble-layout).

## Text and wrapping

| Key | Default | Meaning |
|---|---|---|
| `text` | required | The line. Required — `validate` flags a bubble without it |
| `max_chars` | `22` | Wrap width, in characters |
| `fs` | from `bubble_style` | Font size in px for this bubble |
| `uppercase` | from `bubble_style` | Force this bubble's text to caps |
| `tail` / `tail_bend` / `tail_gap` / `tail_from` | from `bubble_style` | This bubble's tail |

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
| `tail` | `wedge` | `wedge`, `curve`, `line` or `none` |
| `tail_bend` | auto | Bow of a `curve` / `line` tail, `-1..1` |
| `tail_gap` | `12` | Px a `line` tail stops short of its target |
| `tail_from` | auto | Where tails leave: edge, position, or `{edge, pos}` |

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

# raster art: mark the heads, let the layout do the rest
image: "art/03.png"
speakers: {ema: [0.72, 0.3], jan: [0.25, 0.42]}
bubbles:
  - {text: "Kde jsi byl?", speaker: ema}
  - {text: "Venku.",       speaker: jan}
```
