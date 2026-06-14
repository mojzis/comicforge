# Examples (moved to projects/)

The example projects have moved. They now live under [`projects/`](../projects/):

| Project | Spec | About |
|---|---|---|
| `slepice` | `projects/slepice/page.yaml` | Bára hlídá slepice — the original 2×2 demo page. |
| `kosticka` | `projects/kosticka/page.yaml` | Kostička — a short strip with thought/speech/shout bubbles, pixel art, and scene backgrounds (`pokoj`, `dvur`). |
| `dvur-scene` | `projects/dvur-scene/scene.yaml` | A standalone scene illustration (no comic grid) — render with the `scene` command. |

Shared character art is in [`library/characters/`](../library/characters/);
pixel-art sprites are in [`library/pixel/`](../library/pixel/);
scene backgrounds are in [`projects/_scenes/`](../projects/_scenes/).

Render from the repo root:
```bash
uv run --active comicforge render projects/slepice/page.yaml   -o slepice.png
uv run --active comicforge render projects/kosticka/page.yaml  -o kosticka.png
uv run --active comicforge scene  projects/dvur-scene/scene.yaml -o dvur.png
```

For the full authoring reference see [`docs/authoring-guide.md`](../docs/authoring-guide.md).
