# Authoring with Claude

ComicForge was built so that a language model can author comics without any
special integration. Nothing in the engine is aware of an LLM — the affordances
are the same ones that make the tool scriptable:

- **The whole authoring surface is text.** A page is YAML; there is no canvas
  state, no drawing calls, no mouse.
- **The art is machine-readable.** `cmf characters` and `cmf scenes` print JSON
  listing every character, pose, slot and variant that exists.
- **Mistakes are enumerable.** `cmf validate` reports every problem in a spec at
  once, with the legal values, instead of failing on the first one.
- **Feedback is cheap and targeted.** `cmf panel` renders one panel and
  `cmf character` renders one figure, so a correction does not require
  re-reading a whole page.

## The bundled skill

The repository carries an authoring skill at
[`skills/comicforge/`](https://github.com/mojzis/comicforge/tree/main/skills/comicforge) —
`SKILL.md` is the authoring contract, `reference.md` the deeper reference.

`cmf init` copies it into every project it scaffolds:

```
my-comic/
  .claude/skills/comicforge/
    SKILL.md
    reference.md
```

Open that project in [Claude Code](https://claude.com/claude-code) and the skill
loads when the work calls for it — writing a page spec, adding a character,
placing bubbles, answering a question about the grammar. You do not have to
mention it.

Refresh it after upgrading the engine:

```bash
cmf init my-comic --force
```

## The loop that works

Whether the author is a person or a model, the same sequence keeps things
honest:

1. **Read the manifests first.** `cmf characters --library characters` and
   `cmf scenes --scenes scenes`. Never guess a pose or a variant name — the
   manifest is the list of what may legally appear in a spec.
2. **Write the spec** under `pages/`, with `library:`, `scenes_dir:` and
   `pixel_dir:` relative to the spec file.
3. **Validate before rendering.** `cmf validate pages/strip.yaml` catches the
   silent failures — a mistyped slot, an unknown panel key, a `speaker` naming
   nobody — that would otherwise render as a plausible-looking wrong panel.
4. **Render, then look.** `cmf render` for the page, or `cmf panel --row --col`
   for the one panel being worked on.
5. **Adjust `x` / `y` / `scale` / `to` and repeat.**

Step 3 is the one that is easy to skip and expensive to skip. `render` silently
ignores keys it does not recognise, so `fcae: happy` produces a perfectly
rendered default face and no complaint at all.

## Things worth telling a model explicitly

Habits from other tools that do not apply here:

- **Do not crop a full-page render to inspect a panel.** `cmf panel` exists and
  is far cheaper. The same goes for ImageMagick and friends.
- **Read the `.small.png`.** `cmf character` writes a reduced companion image
  beside its output specifically so that reading it back costs fewer tokens.
- **Do not auto-vectorize a generated image.** Tracing destroys the slot
  structure and anchor registration that make a character poseable. Reference
  images are for looking at; the SVG is authored by hand. See
  [Reference images](art/inspire.md).
- **Omit bubble coordinates when in doubt.** Bubbles stack by measured height
  and are clamped inside the panel, so leaving `x` and `y` out is more reliable
  than guessing them — especially over raster panels, where there is no
  `speaker` to anchor to.
- **The engine ships no art.** There is no default character to fall back on. A
  new project starts empty and every asset directory must be named.

## Generating specs from a script

The same contract works without an LLM. Read the manifest, emit YAML, validate,
render:

```python
import yaml
from comicforge.library import Library
from comicforge.validate import validate_spec
from comicforge import render_spec

manifest = Library("characters").manifest()
faces = manifest["tom"]["slots"]["face"]

spec = {
    "page": [200, 60],
    "library": "characters",
    "rows": [{"panels": [
        {"actors": [{"char": "tom", "face": f, "x": 0.5, "y": 0.6, "scale": 0.85}],
         "caption": f}
        for f in faces
    ]}],
}

problems = validate_spec(spec)
assert not problems, problems
render_spec(spec, "faces.png")
```

A dict spec has no file to resolve relative paths against, so `"characters"`
here means "relative to the current working directory" — see
[Python API](reference/python-api.md#passing-libraries-explicitly).

That is how the contact sheets in the [gallery](gallery.md) are made — except
they are checked-in specs rather than generated ones, so they are also
documentation.
