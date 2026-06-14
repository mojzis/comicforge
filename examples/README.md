# Examples

Each subdirectory here is a **self-contained ComicForge project**. There is no
shared asset library — a project owns all of its own art. This mirrors a real
downstream project, which does `pip install comicforge` and brings its own
characters, scenes, and sprites; none of this example art ships with the engine.

A project is laid out as:

```
<project>/
  characters/   base.svg + <slot>-<variant>.svg + character.yaml, per character
  scenes/       base.svg + <slot>-<variant>.svg + scene.yaml, per scene
  pixel/        <name>.yaml (grid + palette), per sprite
  pages/        the comic specs; reference assets via ../characters, ../scenes, ../pixel
```

## `pes`

The demo project — Tom (a person) and Bára (a dog).

| Page | Spec | About |
|---|---|---|
| `slepice` | `pes/pages/slepice.yaml` | Bára hlídá slepice — the original 2×2 demo page. |
| `kosticka` | `pes/pages/kosticka.yaml` | Kostička — a short strip with thought/speech/shout bubbles, pixel art, and scene backgrounds (`pokoj`, `dvur`). |
| `dvur-scene` | `pes/pages/dvur-scene.yaml` | A standalone scene illustration (no comic grid) — render with the `scene` command. |

Render from the repo root:
```bash
uv run --active comicforge render examples/pes/pages/slepice.yaml  -o slepice.png
uv run --active comicforge render examples/pes/pages/kosticka.yaml -o kosticka.png
uv run --active comicforge scene  examples/pes/pages/dvur-scene.yaml -o dvur.png
```

Inspect the project's assets:
```bash
uv run --active comicforge characters --library examples/pes/characters
uv run --active comicforge scenes     --scenes  examples/pes/scenes
```

For the full authoring reference see the authoring skill:
[`../skills/comicforge/SKILL.md`](../skills/comicforge/SKILL.md) (quick contract)
and [`../skills/comicforge/reference.md`](../skills/comicforge/reference.md) (deep dive).
