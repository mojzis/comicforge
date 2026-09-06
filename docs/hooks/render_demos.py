"""MkDocs hook: render every image the docs site shows, at build time.

The site never checks in a PNG. Each picture on these pages comes out of the
engine in the tree, from a spec you can read right next to it — so a change to
the renderer that breaks a demo breaks the docs build, and a screenshot can
never quietly drift from what the code actually draws.

What gets rendered into ``docs/assets/renders/``:

* every spec in ``docs/demos/`` — the small, purpose-built examples that the
  guide pages embed side by side with their YAML source;
* the three demo pages of ``examples/pes/`` — the gallery;
* one panel of a page, to illustrate ``cmf panel``.

Renders are cached against the mtimes of the spec and of the whole project it
draws from, so ``mkdocs serve`` only redraws what actually changed.
"""

from __future__ import annotations

import logging
from pathlib import Path

from comicforge.render import (
    load_spec,
    render_panel,
    render_scene,
    render_spec,
    spec_type,
)

log = logging.getLogger("mkdocs.hooks.render_demos")

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
DEMOS = DOCS / "demos"
OUT = DOCS / "assets" / "renders"
PES = ROOT / "examples" / "pes"
TUTORIAL_ART = DEMOS / "tutorial-art"

# Extra one-off renders beyond "every demo spec": (spec, output stem, kwargs).
PAGES = [
    (TUTORIAL_ART / "pages" / "first.yaml", "tutorial"),
    (PES / "pages" / "slepice.yaml", "slepice"),
    (PES / "pages" / "kosticka.yaml", "kosticka"),
    (PES / "pages" / "dvur-scene.yaml", "dvur-scene"),
]

# One panel of a page, as `cmf panel` would write it.
PANELS = [(PES / "pages" / "kosticka.yaml", "kosticka-r0c1", 0, 1, 1.0)]


def _newest(*paths: Path) -> float:
    """Newest mtime under the given files/dirs (0 when nothing exists)."""
    best = 0.0
    for p in paths:
        if p.is_dir():
            best = max(
                [best, *(f.stat().st_mtime for f in p.rglob("*") if f.is_file())]
            )
        elif p.is_file():
            best = max(best, p.stat().st_mtime)
    return best


def _stale(out: Path, *sources: Path) -> bool:
    return not out.exists() or out.stat().st_mtime < _newest(*sources)


def _render(spec: Path, out: Path, deps: list[Path]) -> None:
    if not _stale(out, spec, *deps):
        return
    kind = spec_type(load_spec(spec))
    draw = render_scene if kind == "scene" else render_spec
    draw(spec, out)
    log.info("rendered %s -> %s", spec.name, out.name)


def on_pre_build(config) -> None:  # MkDocs hook signature: config is unused
    OUT.mkdir(parents=True, exist_ok=True)

    # Demo specs draw from examples/pes and from the tutorial character, so a
    # change to either art tree invalidates the renders.
    deps = [PES, TUTORIAL_ART]
    for spec in sorted(DEMOS.glob("*.yaml")):
        try:
            _render(spec, OUT / f"{spec.stem}.png", deps)
        # A broken demo should name itself in the log; --strict then fails the
        # build on the missing image rather than on an opaque traceback.
        except Exception:
            log.exception("demo %s failed to render", spec.name)

    for spec, stem in PAGES:
        try:
            _render(spec, OUT / f"{stem}.png", deps)
        except Exception:
            log.exception("page %s failed to render", spec.name)

    for spec, stem, row, col, scale in PANELS:
        out = OUT / f"{stem}.png"
        if _stale(out, spec, *deps):
            try:
                render_panel(spec, out, row=row, col=col, scale=scale)
            except Exception:
                log.exception("panel %s failed to render", spec.name)
