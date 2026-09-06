# Reference images

`cmf inspire` blends a project-wide **theme** with per-item **descriptions** and
asks an image model to paint them. The output is **reference art to draw from** —
never a shipped asset.

```bash
cmf inspire references.yaml --dry-run     # compose the prompts, call nothing
cmf inspire references.yaml --review      # generate, plus a review.html grid
```

!!! danger "Do not auto-vectorize the result"

    Tracing a generated image produces thousands of paths in one flat layer.
    That destroys the slot structure and the anchor registration that make a
    character poseable — you end up with a picture, not a character. Look at the
    reference, then author the SVG. See
    [Making a character](characters.md).

## Two files

### `theme.yaml` — the project's look

Applied to every image, so the whole cast comes back in one style.

```yaml title="theme.yaml"
style: >
  Hand-drawn children's-book comic illustration. Bold, clean black ink outlines
  with flat cheerful fills and simple friendly shapes. Light, uncluttered
  background. Centered subject filling the frame.

palette:
  - "#f4d35e"  # sunny yellow
  - "#ee964b"  # warm orange
  - "#0d3b66"  # deep blue
  - "#faf0ca"  # cream
  - "#f95738"  # coral

mood: warm, playful, gentle

negative: No text, no letters, no words, no watermark, no signature.

aspect_ratio: "1:1"
# model: google/imagen-3
```

| Key | Default | Meaning |
|---|---|---|
| `style` | — | The look, in words. Prepended to every prompt |
| `palette` | — | Hex colours fed to the model as a colour scale |
| `mood` | — | One line of tone |
| `negative` | no text / watermark / signature | What to avoid |
| `aspect_ratio` | `"1:1"` | Passed to the model |
| `model` | `google/imagen-3` | Any Replicate model id |

A missing `theme.yaml` is not an error — you just get the defaults.

### `references.yaml` — the things to depict

```yaml title="references.yaml"
items:
  - id: tom
    prompt: >
      A cheerful 8-year-old boy named Tom in a striped t-shirt and shorts,
      full body, standing, neutral friendly expression, simple cartoon style.

  - id: dvur
    prompt: >
      A sunny Czech village farmyard: a wooden fence, a small chicken coop,
      a few hens pecking, a cobbled yard, a tree to one side.
```

Each entry needs an id (`id` or `name`) and a description (`prompt`,
`description` or `desc`). A bare list without the `items:` key works too. The id
becomes the filename.

## The composed prompt

`style` → `Subject: <prompt>` → palette → mood → negative, joined by blank
lines:

```text title="references/tom.prompt.txt"
Hand-drawn children's-book comic illustration. Bold, clean black ink outlines
with flat cheerful fills and simple friendly shapes. Light, uncluttered
background. Centered subject filling the frame.

Subject: A cheerful 8-year-old boy named Tom in a striped t-shirt and shorts,
full body, standing, neutral friendly expression, simple cartoon style.

Use this color palette: #f4d35e, #ee964b, #0d3b66, #faf0ca, #f95738.

Mood: warm, playful, gentle.

No text, no letters, no words, no watermark, no signature.
```

The sidecar is written next to every image, so you can always see exactly what
produced a picture. `--dry-run` writes only the sidecars — use it to iterate on
wording without spending a call or needing a token.

## Output and flags

Each item writes `<out_dir>/<id>.png` and `<out_dir>/<id>.prompt.txt`.
`theme.yaml` and the output directory default to siblings of the references
spec.

```bash
cmf inspire references.yaml -o refs/        # choose the output directory
cmf inspire references.yaml --theme t.yaml  # a different theme
cmf inspire references.yaml --only tom,dvur # a subset
cmf inspire references.yaml --force         # regenerate images that already exist
cmf inspire references.yaml --review        # also write review.html
```

By default an item whose `.png` already exists is skipped, so re-running after
adding one entry costs one call. `--review` writes a `review.html` grid of every
image beside its prompt — the fastest way to judge a batch and decide what to
re-word.

## Setup for live generation

```bash
uv tool install "comicforge[inspire]"      # adds replicate + python-dotenv
export REPLICATE_API_TOKEN=...             # or a .env beside the spec
```

The token is read from the environment, or from a `.env` file next to the
references spec or in the current directory. Live calls are paced — the default
model caps at roughly six requests a minute, so a batch takes about eleven
seconds per image.

Neither the extra nor the token is needed for `--dry-run`.

## How to actually use the output

1. Write the description, run `--dry-run`, read the composed prompt.
2. Generate a handful with `--review` and pick the one that reads best as a
   *shape* — silhouette, proportions, the pose you want as a base.
3. Author `base.svg` by hand from it: clean outlines, flat fills, in one
   viewBox.
4. Draw the overlays around the same head position, and write
   `character.yaml`.
5. Keep the reference in `references/` as documentation of the intent. It never
   goes into `characters/`.

Step 3 is the work, and there is no shortcut through it. The reference exists to
make a design decision, not to become the asset.
