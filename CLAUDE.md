# CLAUDE.md — working on the ComicForge engine

## What ComicForge is

A tiny, scriptable comic-page engine. Characters are a **base SVG + stackable
variant overlays** (faces, arms, …); a comic page is a **declarative YAML spec**;
output is **SVG / PNG / PDF**.

## Repository layout

```
comicforge/              The engine — pure code, no bundled art.
  library.py             loads a character, stacks base+overlays, places it in a panel
  scene.py               loads a scene, stacks overlays, scales it to cover a box
  pixelart.py            grid+palette → SVG sprite (from a dir or inline)
  bubbles.py             speech / thought / shout bubbles with word-wrap + tail
  render.py              row/panel pages + standalone scenes → SVG → PNG/PDF
  inspire.py             theme + descriptions → reference images (Replicate API)
  cli.py                 `render`/`scene`/`panel`/`characters`/`scenes`/`inspire`
  __main__.py            `python -m comicforge` entry point
examples/pes/            A self-contained demo project (characters, scenes, pixel, pages).
                         Develop against the engine the same way a downstream project would.
skills/comicforge/       The portable authoring skill (SKILL.md + reference.md).
tests/                   pytest suite.
```

The engine never imports from `examples/`; the example project is just data the
CLI/tests point at. Keep it that way — no content leaks into `comicforge/`.

## Asset model (what the engine code assumes)

- A **character** is an *identity* (`character.yaml`: name, label, default, slots)
  that owns one or more **poses**. Two on-disk shapes, both loaded by `library.py`:
  - *Flat (single pose):* `base.svg` + `<slot>-<variant>.svg` overlays (all in the
    *same* viewBox) + `character.yaml` (adds `viewbox:`). The classic layout.
  - *Posed (multiple poses):* `character.yaml` lists `poses:` and an `anchor:`
    (the canonical reference point — e.g. head centre — that the **shared** overlays
    are drawn around). Shared overlays (`<slot>-<variant>.svg`, e.g. faces) live at
    the character root; each pose is `poses/<pose>/` with its own `base.svg`,
    `pose.yaml` (`viewbox`, `anchor`, optional pose-specific `slots`/`default`), and
    optional pose-specific overlays. The engine translates shared overlays by
    `pose.anchor - character.anchor` so one face SVG re-registers onto every pose.
    Translate-only — keep the head the same *size* across poses, just moved.
  - Flat = the posed model with one implicit pose at anchor `[0,0]`; both render
    identically, so existing flat characters keep working. `tom` is flat, `bara`
    is posed (`sit`, `walk`) — keep one of each in the demo.
- A **scene** is `base.svg` + overlays + `scene.yaml`; single body (no poses),
  rendered with *cover* scaling. `scene.py` has its own `Scene` dataclass.
- A **pixel sprite** is `grid` (equal-length strings) + `palette` (char→hex); `.`/space
  = transparent. Lives in `<project>/pixel/<name>.yaml` or inline in a spec.
- Three asset dirs feed the engine, each settable in the spec or via CLI flag:
  `library:`/`--library`, `scenes_dir:`/`--scenes`, `pixel_dir:`/`--pixel-dir`.
- **Path resolution:** relative paths in a spec resolve against the *spec file's*
  directory; CLI flags resolve against the cwd and override spec keys.

## Dev loop

Assume an activated venv (`source .venv/bin/activate`); commands below run directly.

```bash
uv sync          # create .venv, install deps (run once)
poe test         # fail-fast tests, no coverage, terse (the tight loop)
poe check        # everything: lint, typecheck, dead-code, deps, clones, vulns, test
poe fix          # auto-format + auto-fix lint
poe cov          # full test run with coverage report
```

`poe test` is the tight loop — quiet, fail-fast, no coverage, minimal tokens.
`poe check` runs the static-analysis tools in parallel then the tests; run it
before declaring work done. See `poe_tasks.toml` for the full task list.

Render the demos to eyeball a change end-to-end:

`cmf` is the short alias for the `comicforge` CLI.

```bash
cmf render examples/pes/pages/slepice.yaml   -o slepice.png
cmf render examples/pes/pages/kosticka.yaml  -o kosticka.png
cmf scene  examples/pes/pages/dvur-scene.yaml -o dvur.png
cmf panel  examples/pes/pages/slepice.yaml -o panels/ --all
```

## Conventions / invariants

- **Content-free engine:** never hardcode an asset name, path, or default project
  in `comicforge/`. A missing required dir raises a clear `ValueError` telling the
  user to set the spec key or pass the flag — preserve that behavior.
- **SVG all the way down**, rasterized only at the end (crisp vector PDF for print).
- The CLI subcommands (`render`/`scene`/`panel`/`characters`/`scenes`) are the
  stable surface; `characters`/`scenes` emit JSON manifests other tools depend on.
- When you change the spec grammar or CLI, update the authoring skill in
  `skills/comicforge/` (both `SKILL.md` and `reference.md`) in the same change.
- Demo art is hand/LLM-authored crisp SVG, edited directly in `examples/pes/`
  (there is no procedural generator). Use `comicforge inspire` for *reference*
  images only — never auto-vectorize them; it breaks overlay/anchor registration.
