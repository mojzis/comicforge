---
title: ComicForge
description: A tiny, scriptable comic-page engine — author comics as YAML, render to SVG / PNG / PDF.
hide:
  - navigation
---

<div class="cf-hero" markdown>

<div markdown>
<p class="cf-hero__tag">YAML in · comics out</p>

# Draw comics by describing them

ComicForge is a tiny, scriptable comic-page engine. A character is a **base SVG
plus stackable overlays** — faces, arms, poses. A page is a **declarative YAML
spec**. The output is **SVG, PNG or PDF**, vector all the way down and rasterized
only at the very end.

There is no timeline, no canvas, no mouse. You say *who is in the panel, where
they stand, and what they say* — and the engine draws it, the same way every
time. Which means a script can write your comic, and so can a language model.

[Start here](quickstart.md){ .md-button .md-button--primary }
[Read the spec](reference/spec.md){ .md-button }
</div>

<div class="cf-hero__art" markdown>
![A three-panel comic strip rendered by ComicForge](assets/renders/strip.png)
</div>

</div>

That strip is not a screenshot. It is rendered from this file, every time these
docs are built:

```yaml title="the whole strip, start to finish"
--8<-- "demos/strip.yaml"
```

---

## Why it is built this way

<div class="grid cards" markdown>

-   :material-file-code:{ .lg .middle } **A page is data**

    ---

    The entire authoring surface is YAML and a JSON manifest of what art exists.
    No API to learn, nothing imperative to sequence. Diff it, template it,
    generate it, review it in a pull request.

-   :material-layers-triple:{ .lg .middle } **Posing is stacking**

    ---

    No rig, no bones, no interpolation. An expression is a small SVG drawn in
    the same canvas as the body; choosing one is choosing a filename. You can
    open any of them in an editor and fix a line by hand.

-   :material-vector-square:{ .lg .middle } **Vector to the last step**

    ---

    Everything composes as SVG and rasterizes once, at the end. A PDF stays
    crisp at print size; a PNG comes out at whatever `px_per_mm` you ask for.

-   :material-package-variant:{ .lg .middle } **The engine ships no art**

    ---

    `comicforge/` contains code and nothing else — no default characters, no
    bundled sprites. Your project owns every asset it draws, so the engine is a
    dependency rather than a content bundle.

</div>

## In sixty seconds

```bash
uv tool install comicforge     # puts `cmf` on your PATH — no venv, no Python project
cmf init my-comic              # scaffold characters/ scenes/ pixel/ pages/
cd my-comic
cmf render pages/hello.yaml    # -> output/hello-<timestamp>.png
```

Then open `pages/hello.yaml`, change a line, render again. That is the whole
loop. [Your first comic](quickstart.md) walks through it properly.

## What a spec can hold

<div class="grid cards" markdown>

-   **[Actors](guide/actors.md)** — characters placed by panel fraction, with a
    pose and a variant per slot.

-   **[Bubbles](guide/bubbles.md)** — speech, thought and shout, word-wrapped,
    auto-placed over whoever is speaking.

-   **[Scenes](guide/scenes.md)** — reusable illustrated backgrounds with their
    own overlay slots, cover-scaled into any panel.

-   **[Captions and frames](guide/captions-frames.md)** — narration bands and
    panel outlines, page-wide or per panel.

-   **[Pixel art](guide/pixel-art.md)** — sprites as a grid of characters and a
    palette, from a file or inline.

-   **[Raster images](guide/images.md)** — drop a finished bitmap in as a panel
    background and compose on top of it.

</div>

## Where to go next

| If you want to… | Read |
|---|---|
| Get something on screen | [Your first comic](quickstart.md) |
| Set up a real project | [Starting a project](starting-a-project.md) |
| Understand the model | [Core concepts](concepts.md) |
| Look up a key | [Spec reference](reference/spec.md) |
| Look up a command | [CLI reference](reference/cli.md) |
| Draw your own characters | [Making the art](art/characters.md) |
| Have Claude write specs | [With Claude](claude.md) |
| See it all working | [Gallery](gallery.md) |
