# CLI reference

Two identical entry points are installed: `comicforge` and the short alias
`cmf`, used throughout these docs. `python -m comicforge` works too.

```bash
cmf --help
cmf <command> --help
```

## Commands at a glance

| Command | Does |
|---|---|
| [`init`](#init) | Scaffold a new data-only project |
| [`render`](#render) | Render a comic page spec |
| [`scene`](#scene) | Render a standalone illustration |
| [`panel`](#panel) | Render one panel, or every panel, for review |
| [`character`](#character) | Render one character on a plain canvas |
| [`validate`](#validate) | Check a spec against its libraries, without drawing |
| [`characters`](#characters) | Print the character manifest as JSON |
| [`scenes`](#scenes) | Print the scene manifest as JSON |
| [`inspire`](#inspire) | Generate reference images from a theme + descriptions |

## Asset directory flags

`render`, `scene`, `panel` and `validate` all accept the same three overrides:

| Flag | Overrides the spec key |
|---|---|
| `--library <dir>` | `library:` |
| `--scenes <dir>` | `scenes_dir:` |
| `--pixel-dir <dir>` | `pixel_dir:` |

A flag wins over the spec key. **Flags resolve against your current working
directory**; relative paths *inside* a spec resolve against the spec file's
directory. That difference is deliberate and it is the single most common source
of confusion — see [path resolution](spec.md#path-resolution).

## Default output

`render`, `scene`, `panel` and `character` all accept `-o` / `--out`. Omit it
and the file lands in a gitignored `output/` directory with a timestamp:

```
output/slepice-20260614-191613.png
output/slepice-r0c1-20260614-191702.png
output/slepice-panels-20260614-191744/
```

Successive renders accumulate side by side, so you can watch a page evolve. Pass
`-o` when you want an exact path. The **format follows the extension** —
`.svg`, `.png` or `.pdf`.

---

## `init`

```bash
cmf init <dir> [--force]
```

Scaffolds a data-only project: the `characters/`, `scenes/`, `pixel/` and
`pages/` asset directories, a renderable `pages/hello.yaml`, a seed
`pixel/heart.yaml`, a `.gitignore`, a project `README.md`, and a copy of the
authoring skill under `.claude/skills/comicforge/`.

Idempotent — files that already exist are left alone and reported as skipped.

| Flag | Meaning |
|---|---|
| `--force` | Overwrite the scaffolded files instead of skipping them |

Re-run with `--force` after upgrading the engine to refresh the bundled skill.

```bash
cmf init my-comic
cmf init my-comic --force        # refresh the skill after an upgrade
```

---

## `render`

```bash
cmf render <spec.yaml> [-o <output>] [--library <dir>] [--scenes <dir>] [--pixel-dir <dir>]
```

Renders a comic **page** — a spec with `rows:`. Handed a `type: scene` spec it
refuses and points you at `cmf scene` rather than crashing.

```bash
cmf render pages/slepice.yaml -o slepice.png
cmf render pages/slepice.yaml -o slepice.pdf     # true vector
cmf render pages/slepice.yaml                    # -> output/slepice-<ts>.png
```

---

## `scene`

```bash
cmf scene <spec.yaml> [-o <output>] [--library <dir>] [--scenes <dir>] [--pixel-dir <dir>]
```

Renders a **standalone illustration** — one background filling the canvas, no
panel grid. Handed a page spec it refuses and points you at `cmf render`.

```bash
cmf scene pages/dvur-scene.yaml -o dvur.png
```

See [Standalone illustrations](../guide/illustrations.md).

---

## `panel`

```bash
cmf panel <spec.yaml> [-o <output>]
  [--row 0] [--col 0] [--all] [--scale 0.5]
  [--library <dir>] [--scenes <dir>] [--pixel-dir <dir>]
```

Renders individual panels of a page for review.

| Flag | Default | Meaning |
|---|---|---|
| `--row` | `0` | Row index, 0-based |
| `--col` | `0` | Column index within the row, 0-based |
| `--all` | off | Render every panel into the `-o` **directory** |
| `--scale` | `0.5` | Size relative to the full-page panel |

```bash
cmf panel pages/strip.yaml --row 0 --col 1
cmf panel pages/strip.yaml --all -o panels/
cmf panel pages/strip.yaml --row 1 --col 0 --scale 1.0
```

With `--all`, files are written as `panel_r<R>c<C>.png`. The default `--scale`
of `0.5` is deliberately low-resolution — this is for looking, not for output.

This is the supported way to inspect one panel. Rendering the whole page and
cropping it with an image tool gets you the same picture for more work.

---

## `character`

```bash
cmf character <name> [selection ...] --library <dir>
  [-o <output>] [--pose <pose>] [--scale 2.0] [--bg "#ffffff"] [--flip] [--thumb-px 320]
```

Renders one character alone on a plain canvas, cropped to its pose — a quick
visual test of a pose or an expression with no page around it.

Each `selection` token is either a **bare name** — matched first against the
character's poses, then against the variants of every slot — or an explicit
`key=value`. An unknown token errors with the available poses and slots listed.

| Flag | Default | Meaning |
|---|---|---|
| `--library` | **required** | Character library directory |
| `--pose` | character's default | Which pose to draw |
| `--scale` | `2.0` | Output px per viewBox unit |
| `--bg` | `#ffffff` | Canvas colour |
| `--flip` | off | Mirror horizontally |
| `--thumb-px` | `320` | Body width of the small companion PNG; `0` to skip it |

```bash
cmf character bara sit happy --library characters
cmf character bara pose=walk face=neutral --library characters
cmf character tom --library characters -o tom.png
```

It writes **two** files: the full render at `-o`, and a smaller
`<stem>.small.png` beside it. When an agent reads the result back, the small one
costs far fewer tokens.

---

## `validate`

```bash
cmf validate <spec.yaml> [--library <dir>] [--scenes <dir>] [--pixel-dir <dir>]
```

Statically checks a page or scene spec against the libraries it points at, and
reports **every** problem at once. Nothing is drawn.

This catches things `render` cannot. `render` stops at the first unrenderable
item, and *silently ignores keys it does not recognise* — so `fcae: happy` or
`post: walk` renders a default-faced, default-posed actor without a word of
complaint. `validate` flags:

- characters, scenes and pixel sprites missing from the library
- poses an actor asks for that the character does not have
- slot variants that do not exist for the chosen character + pose, or scene
- actor and scene keys that are neither reserved nor a real slot — likely typos
- panel keys the renderer does not know, such as `imge:` for `image:`
- raster `image:` files that are missing, unreadable or of an unsupported type;
  an `image:` with no `src`; an unknown image key; an unknown `fit`
- a bubble `speaker` naming no actor in the panel; an unknown bubble `kind`
- structural holes — a page with no `rows`, a row with no `panels`, a bubble
  with no `text`, a scene spec with neither `scene:` nor `image:`
- an unknown `type:`, or a `type:` that contradicts the structure (a `scene`
  spec carrying `rows`)

Exit code `0` when the spec is sound, `1` with a bulleted list otherwise — so it
drops straight into a pre-render check or CI.

```bash
cmf validate pages/slepice.yaml
```

```
pages/slepice.yaml: ok
```

```
pages/strip.yaml: 3 problem(s)
  - r0c0: unknown panel key 'imge' (ignored when rendering). Known: ['actors',
    'bg', 'bubbles', 'caption', 'frame', 'image', 'pixel', 'scene', 'width']
  - r0c0: "character 'tomm' not found in characters. Have: ['bara', 'tom']"
  - r0c0: tom has no slot 'fcae' (ignored when rendering). Slots: ['arms', 'face']
```

`r0c0` is row 0, column 0. Note the phrase *ignored when rendering* — those are
exactly the mistakes that would otherwise cost you nothing but a wrong-looking
panel.

---

## `characters`

```bash
cmf characters --library <dir>
```

Prints the character manifest as JSON: every character, its label, its slots and
their variants, its defaults, and — for multi-pose characters — the pose list
with each pose's own slots.

`--library` is required; there is no default, because the engine ships no art.

```bash
cmf characters --library characters
```

```json
{
  "bara": {
    "label": "Bára",
    "slots": {"face": ["neutral", "happy"]},
    "default": {"pose": "sit", "face": "neutral"},
    "default_pose": "sit",
    "poses": {"sit": {"slots": {}, "default": {}},
              "walk": {"slots": {}, "default": {}}}
  },
  "tom": {
    "label": "Tom",
    "slots": {"arms": ["down", "wave", "point", "crossed", "hips", "thumbsup"],
              "face": ["neutral", "happy", "surprised", "sad", "angry", "laugh", "wink"]},
    "default": {"face": "neutral", "arms": "down"}
  }
}
```

This is a stable machine-readable contract — it is what a generator or an agent
reads before writing a spec.

---

## `scenes`

```bash
cmf scenes --scenes <dir>
```

Prints the scene manifest as JSON: every scene, its label, its slots and their
variants, and its defaults. `--scenes` is required.

```json
{
  "dvur":  {"label": "Dvůr",  "slots": {"weather": ["clear", "rain"]},
            "default": {"weather": "clear"}},
  "pokoj": {"label": "Pokoj", "slots": {}, "default": {}}
}
```

---

## `inspire`

```bash
cmf inspire <references.yaml> [-o <dir>]
  [--theme <theme.yaml>] [--only id1,id2] [--force] [--dry-run] [--review]
```

Generates **reference** images from a project theme plus per-item descriptions.
Not shipped assets — see [Reference images](../art/inspire.md).

| Flag | Default | Meaning |
|---|---|---|
| `-o` | `references/` beside the spec | Output directory |
| `--theme` | `theme.yaml` beside the spec | Theme file |
| `--only` | all | Comma-separated ids to generate |
| `--force` | off | Regenerate even when a `.png` already exists |
| `--dry-run` | off | Compose prompts only — no API call, no token needed |
| `--review` | off | Also write a `review.html` grid of images and prompts |

Each item writes `<id>.png` and `<id>.prompt.txt`. Live generation needs the
optional extra and a `REPLICATE_API_TOKEN`:

```bash
uv tool install "comicforge[inspire]"
export REPLICATE_API_TOKEN=...
cmf inspire references.yaml --review
cmf inspire references.yaml --dry-run     # no token required
```

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | `validate` found problems, or a render failed with a spec error (the message names the file and the cause) |
| `2` | Bad command line — `argparse`'s own usage error |
