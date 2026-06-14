"""Generate reference images from a project theme + per-item descriptions.

These images are **inspiration** for hand/LLM-authored SVG art — they are *not*
shipped assets. The idea: describe a character or scene in words, blend it with a
project-wide theme (style, color scale, mood), and let an image model paint a
reference to author crisp SVG from. Do not auto-vectorize the output; it breaks
overlay registration and the editable slot structure.

    comicforge inspire examples/pes/references.yaml

Requires the optional `inspire` extra::

    pip install "comicforge[inspire]"

and a ``REPLICATE_API_TOKEN`` (read from the environment, or a ``.env`` file next
to the references spec / in the cwd). Use ``--dry-run`` to preview the composed
prompts without calling the API (and without needing a token).
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_MODEL = "google/imagen-3"
DEFAULT_ASPECT = "1:1"
# Imagen on Replicate caps at ~6 req/min; pause between live calls.
RATE_LIMIT_SECONDS = 11


@dataclass
class Theme:
    """Project-wide style applied to every generated reference image."""

    style: str = ""
    palette: list[str] = field(default_factory=list)
    mood: str = ""
    negative: str = "No text, no letters, no words, no watermark, no signature."
    aspect_ratio: str = DEFAULT_ASPECT
    model: str = DEFAULT_MODEL


@dataclass
class Item:
    """One thing to depict: an id (→ filename) and a free-text description."""

    id: str
    prompt: str


def load_theme(path: Path) -> Theme:
    """Load ``theme.yaml``. A missing file yields an empty (defaults) theme."""
    if not path.exists():
        return Theme()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    palette = data.get("palette") or []
    if isinstance(palette, str):
        palette = [palette]
    return Theme(
        style=str(data.get("style", "")).strip(),
        palette=[str(c) for c in palette],
        mood=str(data.get("mood", "")).strip(),
        negative=str(data.get("negative", Theme.negative)).strip(),
        aspect_ratio=str(data.get("aspect_ratio", DEFAULT_ASPECT)),
        model=str(data.get("model", DEFAULT_MODEL)),
    )


def load_items(path: Path) -> list[Item]:
    """Load the references spec — a bare list, or a mapping with ``items:``.

    Each entry needs an id (``id`` / ``name``) and a description
    (``prompt`` / ``description`` / ``desc``).
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw = data.get("items", []) if isinstance(data, dict) else data
    if not isinstance(raw, list):
        # malformed config, not a type bug -> ValueError is the right contract
        raise ValueError(  # noqa: TRY004
            f"{path}: expected a list of items (or an 'items:' key)"
        )
    items: list[Item] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: item {i} is not a mapping")  # noqa: TRY004
        ident = entry.get("id") or entry.get("name")
        prompt = entry.get("prompt") or entry.get("description") or entry.get("desc")
        if not ident or not prompt:
            raise ValueError(f"{path}: item {i} needs both an id and a prompt")
        items.append(Item(id=str(ident), prompt=str(prompt).strip()))
    return items


def build_prompt(theme: Theme, item: Item) -> str:
    """Compose the final image prompt: theme style + subject + palette + mood."""
    parts: list[str] = []
    if theme.style:
        parts.append(theme.style)
    parts.append(f"Subject: {item.prompt}")
    if theme.palette:
        parts.append("Use this color palette: " + ", ".join(theme.palette) + ".")
    if theme.mood:
        parts.append(f"Mood: {theme.mood}.")
    if theme.negative:
        parts.append(theme.negative)
    return "\n\n".join(parts)


def _load_dotenv(*dirs: Path) -> None:
    """Best-effort: load a ``.env`` from the given dirs if python-dotenv is present."""
    try:
        from dotenv import (  # noqa: PLC0415  # ty: ignore[unresolved-import]
            load_dotenv,
        )
    except ImportError:
        return
    for d in dirs:
        env = d / ".env"
        if env.exists():
            load_dotenv(env)


def _generate_one(model: str, prompt: str, aspect_ratio: str) -> bytes:
    """Call Replicate and return the raw image bytes."""
    # lazy: only needed for live generation, keeps Replicate an optional dep
    import replicate  # noqa: PLC0415  # ty: ignore[unresolved-import]

    output = replicate.run(
        model,
        input={
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
        },
    )
    # Imagen returns a single FileOutput; some models return a list.
    if isinstance(output, list):
        output = output[0]
    if hasattr(output, "read"):
        return output.read()
    raise RuntimeError(f"unexpected Replicate output: {type(output).__name__}")


def generate(
    refs_path: Path,
    out_dir: Path | None = None,
    *,
    theme_path: Path | None = None,
    only: set[str] | None = None,
    force: bool = False,
    review: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    """Generate reference images for every item in ``refs_path``.

    Paths in the spec resolve against the spec's own directory. ``theme.yaml`` and
    the output ``references/`` dir default to siblings of the spec. Each item
    writes ``<id>.png`` plus an ``<id>.prompt.txt`` sidecar; ``--dry-run`` writes
    only the sidecars. Returns the list of files written.
    """
    refs_path = refs_path.resolve()
    base = refs_path.parent
    theme = load_theme(theme_path.resolve() if theme_path else base / "theme.yaml")
    items = load_items(refs_path)
    out_dir = (out_dir or base / "references").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run:
        _load_dotenv(base, Path.cwd())

    written: list[Path] = []
    targets = [it for it in items if only is None or it.id in only]
    print(f"[inspire] {len(targets)} item(s) → {out_dir}  (model: {theme.model})")  # noqa: T201

    for item in targets:
        prompt = build_prompt(theme, item)
        prompt_path = out_dir / f"{item.id}.prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        written.append(prompt_path)

        img_path = out_dir / f"{item.id}.png"
        if dry_run:
            print(f"  {item.id}: prompt written (dry-run)")  # noqa: T201
            continue
        if img_path.exists() and not force and only is None:
            print(f"  {item.id}: cached, skipping")  # noqa: T201
            continue

        print(f"  {item.id}: generating…")  # noqa: T201
        try:
            data = _generate_one(theme.model, prompt, theme.aspect_ratio)
        except Exception as e:  # surface and keep going on the rest
            print(f"  {item.id}: FAILED — {e}")  # noqa: T201
            continue
        img_path.write_bytes(data)
        written.append(img_path)
        print(f"  {item.id}: wrote {img_path.name} ({len(data) // 1024} KB)")  # noqa: T201
        time.sleep(RATE_LIMIT_SECONDS)

    if review:
        written.append(_write_review(out_dir, targets))

    return written


def _write_review(out_dir: Path, items: list[Item]) -> Path:
    """Write a self-contained HTML grid of the generated images + prompts."""
    cards: list[str] = []
    for item in items:
        img_path = out_dir / f"{item.id}.png"
        if img_path.exists():
            b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
            src = f"data:image/png;base64,{b64}"
        else:
            src = ""
        prompt_path = out_dir / f"{item.id}.prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        cards.append(
            f'<div class="card">'
            f'<img src="{src}" alt="{item.id}" loading="lazy">'
            f"<div class=label>{item.id}</div>"
            f"<details><summary>prompt</summary><pre>{prompt}</pre></details>"
            f"</div>"
        )
    html = (
        "<!doctype html><meta charset=utf-8><title>inspire review</title>"
        "<style>body{font-family:sans-serif;padding:2rem;background:#fafafa}"
        ".grid{display:grid;gap:1.5rem;"
        "grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}"
        ".card{background:#fff;border-radius:12px;padding:1rem;text-align:center;"
        "box-shadow:0 2px 8px rgba(0,0,0,.08)}"
        ".card img{width:100%;border-radius:8px;background:#f0f0f0}"
        ".label{margin-top:.5rem;font-weight:600}"
        "details{margin-top:.5rem;text-align:left}"
        "pre{font-size:.75rem;white-space:pre-wrap;background:#f5f5f5;"
        "padding:.5rem;border-radius:4px}</style>"
        f"<h1>inspire review · {len(items)} item(s)</h1>"
        f"<div class=grid>{''.join(cards)}</div>"
    )
    path = out_dir / "review.html"
    path.write_text(html, encoding="utf-8")
    return path
