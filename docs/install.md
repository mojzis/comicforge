# Install

ComicForge is a Python package with a command-line entry point. A comic project
that uses it, though, is **not a Python project** — it is a directory of YAML
and SVG. So the normal way to install ComicForge is once, globally, the way you
would install any other CLI tool.

## As a tool (recommended)

=== "uv"

    ```bash
    uv tool install comicforge
    ```

=== "pipx"

    ```bash
    pipx install comicforge
    ```

=== "pip"

    ```bash
    pip install comicforge
    ```

All three put two identical commands on your `PATH`:

```bash
cmf --help          # the short alias, used throughout these docs
comicforge --help   # the long name
```

To install straight from the repository instead of PyPI:

```bash
uv tool install git+https://github.com/mojzis/comicforge
```

## Requirements

| | |
|---|---|
| Python | 3.13 or newer |
| System library | **Cairo** — `cairosvg` loads `libcairo` at runtime, and it is not a pip dependency |

Cairo is already present on most desktop Linux installs and on macOS via
Homebrew. If a render fails with `no library called "cairo-2" was found`,
install it:

=== "Debian / Ubuntu"

    ```bash
    sudo apt-get install libcairo2
    ```

=== "Fedora"

    ```bash
    sudo dnf install cairo
    ```

=== "Arch"

    ```bash
    sudo pacman -S cairo
    ```

=== "macOS"

    ```bash
    brew install cairo
    ```

Everything else — `pyyaml`, `cairosvg`, `rich` — comes in with the package.

## The `inspire` extra

[`cmf inspire`](art/inspire.md) generates *reference* images through the
Replicate API, to draw from. It is optional and off the critical path, so its
dependencies live behind an extra:

```bash
uv tool install "comicforge[inspire]"
export REPLICATE_API_TOKEN=...      # or a .env file beside the spec
```

You do not need the extra, or a token, to compose and preview prompts with
`--dry-run`.

## Verify

```bash
cmf init /tmp/cf-smoke
cmf render /tmp/cf-smoke/pages/hello.yaml -o /tmp/cf-smoke/hello.png
```

If that writes a PNG, everything is wired up.

## Pinning a version

`uv tool` installs are global and single-version, which is fine until two
projects need different engine versions. When that happens, give the project a
one-dependency `pyproject.toml` and run through `uv run` instead — see
[Starting a project](starting-a-project.md#when-you-need-more).

## As a library

If you are writing your own render scripts, install it as a normal dependency
and use the [Python API](reference/python-api.md):

```bash
uv add comicforge
```

## Working on the engine itself

```bash
git clone https://github.com/mojzis/comicforge
cd comicforge
uv sync          # create .venv and install dev dependencies
uv run poe test  # the tight loop
```

See [Contributing](contributing.md) for the full task list.
