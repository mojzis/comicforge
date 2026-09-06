---
title: Gallery
description: Everything the engine can draw, rendered from the specs beside it.
---

# Gallery

Every image on this site — this page included — is rendered when the
documentation is built, from the spec printed underneath it. Nothing here is a
screenshot, so nothing here can drift from what the code actually draws.

The art comes from `examples/pes/`, the demo project in the repository. It ships
with the *source*, never with the *package*: the engine itself contains no art
at all.

## A page

<figure class="cf-demo" markdown>
![A four-panel A4 comic page: Tom asks Bára to watch the chickens](assets/renders/slepice.png)
<figcaption><code>examples/pes/pages/slepice.yaml</code> — a 2 × 2 A4 page, no scenes, three pixel sprites, all three bubble kinds.</figcaption>
</figure>

```yaml
--8<-- "examples/pes/pages/slepice.yaml"
```

```bash
cmf render examples/pes/pages/slepice.yaml -o slepice.png
```

## A page with scene backgrounds

<figure class="cf-demo" markdown>
![A three-panel page with illustrated backgrounds](assets/renders/kosticka.png)
<figcaption><code>examples/pes/pages/kosticka.yaml</code> — scenes (<code>pokoj</code>, <code>dvur</code>), pixel art, and manually placed bubbles.</figcaption>
</figure>

```yaml
--8<-- "examples/pes/pages/kosticka.yaml"
```

## One panel of it

<figure class="cf-demo" markdown>
![A single panel: Tom and Bára in the farmyard](assets/renders/kosticka-r0c1.png)
<figcaption><code>cmf panel examples/pes/pages/kosticka.yaml --row 0 --col 1</code></figcaption>
</figure>

## A standalone illustration

<figure class="cf-demo" markdown>
![A wide farmyard illustration with Tom waving and Bára beside him](assets/renders/dvur-scene.png)
<figcaption><code>examples/pes/pages/dvur-scene.yaml</code> — one background filling the canvas. Rendered with <code>cmf scene</code>.</figcaption>
</figure>

```yaml
--8<-- "examples/pes/pages/dvur-scene.yaml"
```

## A strip, with everything at once

<figure class="cf-demo" markdown>
![A three-panel strip with a title, captions, scenes, sprites and all three bubble kinds](assets/renders/strip.png)
<figcaption>Title, page-wide frame and lettering, two scenes, captions, pixel sprites, three bubble kinds.</figcaption>
</figure>

```yaml
--8<-- "demos/strip.yaml"
```

## Contact sheets

Every variant of one slot, as a grid of panels — a useful thing to keep in a
project of your own as art documentation that cannot go stale.

<figure class="cf-demo" markdown>
![Tom's seven face variants](assets/renders/faces.png)
<figcaption>The <code>face</code> slot. The last panel omits <code>face:</code> and gets the default.</figcaption>
</figure>

<figure class="cf-demo" markdown>
![Tom's six arms variants](assets/renders/arms.png)
<figcaption>The <code>arms</code> slot, with <code>face: happy</code> held constant.</figcaption>
</figure>

<figure class="cf-demo" markdown>
![Bára sitting, walking and walking flipped](assets/renders/poses.png)
<figcaption>Two poses and a <code>flip</code>. The faces are shared files, re-registered onto each body by anchor.</figcaption>
</figure>

<figure class="cf-demo" markdown>
![The dvur scene clear and raining, and the pokoj interior](assets/renders/scenes.png)
<figcaption>A scene slot: one background, two weathers — plus a second scene with no slots.</figcaption>
</figure>

## Layout and lettering

<figure class="cf-demo" markdown>
![Two rows of panels with different relative widths and heights](assets/renders/grid.png)
<figcaption>Row <code>height</code> and panel <code>width</code> as relative weights.</figcaption>
</figure>

<figure class="cf-demo" markdown>
![Three panels with different frame settings](assets/renders/frames.png)
<figcaption>Page-default frame, <code>width: 0</code>, and a heavy round red override.</figcaption>
</figure>

<figure class="cf-demo" markdown>
![Bubbles at all nine anchor positions](assets/renders/bubble-at.png)
<figcaption>The nine <code>at:</code> anchors. Each column keeps its own top and bottom stack.</figcaption>
</figure>

<figure class="cf-demo" markdown>
![Three bubbles of different lengths stacked without overlapping](assets/renders/bubble-stack.png)
<figcaption>No coordinates at all — bubbles stack by their measured height.</figcaption>
</figure>

## Raster panels

<figure class="cf-demo" markdown>
![An image cover-cropped, letterboxed, and composed on](assets/renders/images.png)
<figcaption><code>fit: cover</code>, <code>fit: contain</code>, and an actor plus a bubble on top of a bitmap.</figcaption>
</figure>

## Render them yourself

```bash
git clone https://github.com/mojzis/comicforge && cd comicforge
uv sync
uv run cmf render examples/pes/pages/slepice.yaml   -o slepice.png
uv run cmf render examples/pes/pages/kosticka.yaml  -o kosticka.png
uv run cmf scene  examples/pes/pages/dvur-scene.yaml -o dvur.png
```
