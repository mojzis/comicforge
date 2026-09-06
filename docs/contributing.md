# Contributing

## Setup

```bash
git clone https://github.com/mojzis/comicforge
cd comicforge
uv sync            # create .venv and install dev dependencies
```

Cairo must be present on the system — `cairosvg` loads it at runtime and it is
not a pip dependency. See [Install › Requirements](install.md#requirements).

## The task list

```bash
uv run poe test    # fail-fast tests, no coverage, terse — the tight loop
uv run poe check   # everything: lint, typecheck, dead code, deps, clones, vulns, tests
uv run poe fix     # auto-format and auto-fix lint
uv run poe cov     # full test run with a coverage report
```

`poe test` is the loop you run constantly: quiet, fail-fast, minimal output.
`poe check` runs the static-analysis tools in parallel and then the tests — run
it before opening a pull request. The full list lives in `poe_tasks.toml`.

Individual tools: `poe lint` (ruff), `poe typecheck` (ty), `poe dead-code`
(vulture), `poe unused-deps` (deptry), `poe clones` (biston, advisory),
`poe vulns` (pysentry, advisory).

## Repository layout

```
comicforge/              the engine — pure code, no bundled art
  library.py             loads a character, stacks base + overlays, places it
  scene.py               loads a scene, stacks overlays, cover-scales it
  pixelart.py            grid + palette -> SVG sprite
  bubbles.py             speech / thought / shout, word-wrap and tails
  caption.py             narration bands
  raster.py              embedding a bitmap panel background
  render.py              rows / panels / standalone scenes -> SVG -> PNG / PDF
  validate.py            static checks of a spec against its libraries
  inspire.py             theme + descriptions -> reference images
  scaffold.py            `cmf init`
  cli.py                 the command-line surface
examples/pes/            a self-contained demo project
skills/comicforge/       the portable authoring skill
docs/                    this site
tests/                   pytest suite
```

## The rules that matter

**The engine is content-free.** Never hardcode an asset name, a path, or a
default project inside `comicforge/`. A missing required directory raises a
`ValueError` naming the spec key or the CLI flag to set — preserve that
behaviour, and never add a silent fallback.

**No content leaks into the engine.** `comicforge/` must not import anything
from `examples/`. The example project is data the CLI and the tests point at,
nothing more. Develop against it the way a downstream project would.

**SVG all the way down.** Compose as markup; rasterize once, at the end. A PDF
must stay true vector.

**The CLI and the manifests are the stable surface.** `render`, `scene`,
`panel`, `character`, `validate`, `characters`, `scenes` and the JSON they emit
are what other tools depend on. Changing them is a breaking change.

**Keep the skill in sync.** When you change the spec grammar or the CLI, update
`skills/comicforge/SKILL.md` *and* `skills/comicforge/reference.md` in the same
commit — and the affected pages of this site.

**Demo art is hand-authored SVG.** There is no procedural generator. Use
`cmf inspire` for reference images only, and never auto-vectorize them: it
breaks overlay and anchor registration.

## Working on the documentation

The site is [MkDocs Material](https://squidfunk.github.io/mkdocs-material/):

```bash
uv sync --group docs
uv run mkdocs serve     # http://127.0.0.1:8000, live reload
uv run mkdocs build     # into site/
```

Every picture on the site is **rendered at build time** by
`docs/hooks/render_demos.py`, from a spec in `docs/demos/` or from
`examples/pes/`. Nothing is checked in as a screenshot, which means a renderer
change that breaks a demo breaks the docs build.

To add an illustrated example:

1. Write a small spec in `docs/demos/<name>.yaml`. Keep the page small — a
   custom `page: [w, h]` rather than A4 — and point `library:` at
   `../../examples/pes/characters`.
2. Run `cmf validate docs/demos/<name>.yaml`.
3. Reference the render from a page as `assets/renders/<name>.png`, and include
   the source next to it in a tab pair — a `figure.cf-demo` for the picture,
   and a `yaml` block whose body is a
   [snippet](https://facelessuser.github.io/pymdown-extensions/extensions/snippets/)
   include of `demos/<name>.yaml`, so the spec on the page is the same file that
   was rendered.

Look at `docs/guide/bubbles.md` for the pattern. The hook caches on mtime, so
`mkdocs serve` only redraws what changed.

## Tests

`tests/` covers the engine against `examples/pes/`. A change to the renderer
that alters output should come with a test that pins the new behaviour; a change
to the spec grammar should come with a `validate` test for the failure mode as
well as the success.

## Pull requests

- Branch off `main`.
- `uv run poe check` must pass.
- Update the skill and the docs in the same change when the surface moves.
- CI runs the same checks on Linux with `libcairo2` installed, plus a job that
  verifies the `inspire` extra resolves and imports.

## Releases

Tag `vX.Y.Z` matching the version in `pyproject.toml`. The release workflow
builds the sdist and wheel, verifies the tag matches the package version,
creates a GitHub release, and publishes to PyPI through trusted publishing —
no API token involved.
