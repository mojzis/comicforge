# Python API

Most projects never import ComicForge — the CLI is the interface, and a project
is data. Reach for the API when you are generating specs programmatically,
building a preview server, or writing tests around your own art.

```python
from comicforge import render_spec, render_scene, load_spec, PixelLibrary
```

## Rendering

### `render_spec(spec, out_path, library=None, scenes=None, pixel_library=None)`

Renders a comic page. `spec` is a path *or* a dict. The output format comes from
`out_path`'s extension (`.svg`, `.png`, `.pdf`). Returns the composed SVG as a
string.

```python
from comicforge import render_spec

render_spec("pages/slepice.yaml", "slepice.pdf")
svg = render_spec("pages/slepice.yaml", "slepice.svg")
```

### `render_scene(spec, out_path, …)`

The same, for a standalone illustration (`type: scene`).

```python
from comicforge import render_scene

render_scene("pages/dvur-scene.yaml", "dvur.png")
```

Each refuses the other's spec type with a message naming the right function.

### `load_spec(path)`

Reads and parses a spec into a plain dict — useful for inspecting or
transforming one before rendering.

```python
from comicforge import load_spec

spec = load_spec("pages/slepice.yaml")
spec["px_per_mm"] = 8
```

!!! warning "A dict spec has no directory"

    Relative paths in a spec resolve against **the spec file's** directory. A
    dict has no such directory, so its relative paths fall back to the current
    working directory instead — `library: "../characters"` will mean something
    different depending on where the process runs. Use absolute paths, pass
    `spec_dir=` to the `build_*` functions, or build the libraries yourself and
    pass them in.

## Passing libraries explicitly

The three library objects override the spec's own keys, exactly as the CLI flags
do. This is how you render a dict spec, and how you avoid re-reading the same
art for every page in a batch — each library caches what it loads.

```python
from comicforge import render_spec
from comicforge.library import Library
from comicforge.scene import SceneLibrary
from comicforge.pixelart import PixelLibrary

lib    = Library("characters")
scenes = SceneLibrary("scenes")
pixel  = PixelLibrary("pixel")

for page in ("slepice", "kosticka"):
    render_spec(f"pages/{page}.yaml", f"out/{page}.png",
                library=lib, scenes=scenes, pixel_library=pixel)
```

## Panels

```python
from comicforge.render import render_panel, render_all_panels

render_panel("pages/strip.yaml", "panel.png", row=0, col=1, scale=1.0)
paths = render_all_panels("pages/strip.yaml", "panels/", scale=0.5, ext=".png")
```

`render_all_panels` writes `panel_r<R>c<C>.<ext>` into the directory and returns
the list of paths.

## One character

```python
from comicforge.render import render_character
from comicforge.library import Library

lib = Library("characters")
render_character("bara", "bara.png", {"face": "happy"}, pose="walk",
                 library=lib, scale=2.0, bg="#ffffff", flip=False)
```

## Building SVG without writing a file

Every renderer has a `build_*` counterpart that returns the SVG string and
touches no disk:

```python
from comicforge.render import (
    build_svg,            # a page
    build_scene_svg,      # a standalone illustration
    build_panel_svg,      # one panel
    build_character_svg,  # one character
)

svg = build_svg(spec, library=lib, scenes=scenes, spec_dir=Path("pages"))
```

Pass `spec_dir` when the spec came from a dict but its relative paths should
still resolve — it is the directory they resolve against.

## Validation

```python
from comicforge.validate import validate_spec

problems = validate_spec("pages/strip.yaml")
if problems:
    for p in problems:
        print(p)
```

Returns a list of strings, empty when the spec is sound. It never raises for a
bad spec — that is the point.

```python
from comicforge.validate import check_spec

report = check_spec("pages/strip.yaml")
report.problems   # the same list validate_spec returns
report.warnings   # bubble layout warnings, computed only when there are no problems
```

## Bubble layout

### `bubble_layout(spec, row=0, col=0, spec_dir=None)`

Where every bubble of one panel lands, without rendering — for an editor that
draws handles over a panel. `spec` is a dict or a path; a scene spec is its own
single panel. Every point is in panel fractions of the art box (the panel less
its caption band), the same units the spec uses.

```python
from comicforge import bubble_layout

layout = bubble_layout("pages/strip.yaml", row=0, col=1)
```

```python
{"width": 492.0, "height": 307.5,            # art box, page px
 "speakers": {"hen": [0.42, 0.78]},          # every resolvable speaker point
 "bubbles": [
   {"index": 0, "text": "Kvok!", "kind": "speech", "speaker": "hen",
    "auto": True,                            # placed in reading order
    "center": [0.2, 0.08], "box": [0.12, 0.02, 0.28, 0.14],  # x0, y0, x1, y1
    "tail": {"edge": "b", "shape": "wedge",
             "bend": 0.0,                    # -1..1, the resolved bow
             "start": [0.21, 0.14],          # where it leaves the bubble
             "control": [0.22, 0.21],        # the quadratic control point
             "tip": [0.24, 0.29],            # where the drawn tail ends
             "target": [0.42, 0.78]}},       # what it aims at; tail is None
                                             # without a target or with `tail: none`
 ],
 "warnings": []}                             # as `cmf validate` words them
```

`comicforge.render.panel_bubble_layout(panel, width, height, bubble_style)`
does the same for a bare panel dict and an art-box size you already know.

## Panel layout

### `panel_layout(spec, spec_dir=None, on_page=False, ext=".png")`

Where every panel of a page sits, in page px, without rendering — to place the
panel renders again as the page does. The JSON `cmf panel --layout` prints and
`--all` writes as `layout.json`; see [`panel`](cli.md#panel) for the shape.
`image` is the area a panel render covers: the panel `box`, or with `on_page`
the box plus half a gutter. `file` is the name `--all` gives it, with `ext`.

```python
from comicforge import panel_layout

for p in panel_layout("pages/strip.yaml", on_page=True)["panels"]:
    print(p["file"], p["image"])
```

## The manifests

```python
from comicforge.library import Library
from comicforge.scene import SceneLibrary

Library("characters").manifest()     # same JSON as `cmf characters`
SceneLibrary("scenes").manifest()    # same JSON as `cmf scenes`
```

Use these to drive a generator: read what art exists, then emit specs that only
reference variants that are really there.

## Measuring things

Occasionally you need a size before you render — to pick a row height, or to
decide whether a line will fit.

```python
from comicforge import caption
from comicforge.bubbles import bubble_size, text_width

caption.height("Later that afternoon.", {"font_size": 13})
bubble_size("Ahoj!", "speech", max_chars=22, fs=16)
text_width("Ahoj!", 16)
```

Widths are estimates from per-glyph advance tables, not real font metrics —
close enough to lay out a bubble, not exact.

## Scaffolding

```python
from comicforge.scaffold import init_project

created = init_project("my-comic", force=False)   # list of Paths written
```

## Stability

The CLI subcommands and the JSON manifests are the stable surface — other tools
depend on them. The Python functions above are stable in practice but not
versioned as an API contract; if you build on the internals (`Character`,
`Pose`, `Scene`, `cover`, `place`), pin the engine version.
