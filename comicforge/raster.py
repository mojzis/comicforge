"""Embed a raster image (PNG / JPEG / GIF / WebP) as a panel background.

A panel's ``image:`` is the bitmap counterpart of ``scene:``: instead of an SVG
base plus stackable overlays, one finished picture fills the panel.  It is
scaled to *cover* the panel and centre-cropped — the same behaviour
:func:`comicforge.scene.cover` gives a vector scene — so a 3:2 image in a 4:3
panel crops rather than distorts.  ``fit: contain`` letterboxes it instead.

The image is embedded as a base64 ``data:`` URI rather than linked, so an
``.svg`` / ``.pdf`` render is a single self-contained file that keeps working
when it is moved or mailed.  That does mean the output carries the full weight
of every image it uses.

Cropping is done by the panel's clip path (see ``render._render_panel``), which
every panel and standalone scene already establishes.
"""

from __future__ import annotations

import struct
from base64 import b64encode
from pathlib import Path

MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# fit name -> SVG preserveAspectRatio: 'slice' crops the overflow, 'meet' fits
# the whole image inside the box and letterboxes the remainder.
FITS = {"cover": "xMidYMid slice", "contain": "xMidYMid meet"}


def normalize(value) -> dict:
    """Normalise a panel's ``image:`` value to a ``{src, fit}``-shaped dict.

    Accepts the short form (``image: art/01.png``) and the long form
    (``image: {src: art/01.png, fit: contain}``).
    """
    if isinstance(value, str):
        return {"src": value}
    if isinstance(value, dict):
        return value
    raise ValueError(
        f"image must be a path or a {{src, fit}} mapping, got {type(value).__name__}"
    )


def resolve(value, spec_dir: Path | None) -> Path:
    """Resolve an ``image:`` value to a path, relative to the spec file's dir.

    Mirrors ``render._resolve_dir``: relative paths resolve against *spec_dir*
    when it is known (i.e. the spec came from a file), absolute ones are used
    as-is.
    """
    src = normalize(value).get("src")
    if not src:
        raise ValueError("image entry has no 'src' (use `image: path/to/art.png`)")
    p = Path(src)
    if not p.is_absolute() and spec_dir is not None:
        p = spec_dir / p
    return p.resolve()


def data_uri(path: Path) -> str:
    """Read *path* and return it as a base64 ``data:`` URI."""
    mime = MIME.get(path.suffix.lower())
    if mime is None:
        raise ValueError(
            f"unsupported image type '{path.suffix}' for {path}. "
            f"Supported: {sorted(MIME)}"
        )
    return f"data:{mime};base64,{b64encode(path.read_bytes()).decode('ascii')}"


def size(path: Path) -> tuple[int, int]:
    """Read *path*'s pixel dimensions straight out of its header.

    Only the header is parsed — no image library, so ComicForge stays a
    three-dependency package.  A standalone ``type: scene`` spec backed by an
    ``image:`` needs this to size its canvas; a panel does not (the panel box
    already has a size, and ``preserveAspectRatio`` does the fitting).
    """
    head = path.read_bytes()[:64]
    try:
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return struct.unpack(">II", head[16:24])  # IHDR width, height
        if head.startswith(b"GIF8"):
            return struct.unpack("<HH", head[6:10])
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return _webp_size(head)
        if head.startswith(b"\xff\xd8"):
            return _jpeg_size(path)
    except (struct.error, IndexError, ValueError) as e:
        raise ValueError(f"cannot read image dimensions from {path}: {e}") from e
    raise ValueError(f"cannot read image dimensions from {path}: unrecognised header")


def _webp_size(head: bytes) -> tuple[int, int]:
    fmt = head[12:16]
    if fmt == b"VP8X":
        w = int.from_bytes(head[24:27], "little") + 1
        h = int.from_bytes(head[27:30], "little") + 1
        return w, h
    if fmt == b"VP8L":
        bits = int.from_bytes(head[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if fmt == b"VP8 ":
        w, h = struct.unpack("<HH", head[26:30])
        return w & 0x3FFF, h & 0x3FFF
    raise ValueError(f"unknown WebP variant {fmt!r}")


# JPEG start-of-frame markers carry the dimensions; DHP/DAC/RSTn do not.
_SOF = {*range(0xC0, 0xD0)} - {0xC4, 0xC8, 0xCC}


def _jpeg_size(path: Path) -> tuple[int, int]:
    """Walk the JPEG segment chain to the first start-of-frame marker."""
    with path.open("rb") as fh:
        fh.read(2)  # SOI
        while True:
            byte = fh.read(1)
            while byte == b"\xff":  # markers may be padded with 0xff
                byte = fh.read(1)
            if not byte:
                raise ValueError("no start-of-frame marker")
            marker = byte[0]
            (length,) = struct.unpack(">H", fh.read(2))
            if marker in _SOF:
                _precision, h, w = struct.unpack(">BHH", fh.read(5))
                return w, h
            fh.seek(length - 2, 1)


def place(value, spec_dir: Path | None, px, py, pw, ph) -> str:
    """Place an ``image:`` value so it covers the (px, py, pw, ph) box, centred."""
    fit = normalize(value).get("fit", "cover")
    par = FITS.get(fit)
    if par is None:
        raise ValueError(f"unknown image fit '{fit}'. Use one of {sorted(FITS)}")
    uri = data_uri(resolve(value, spec_dir))
    return (
        f'<image x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
        f'preserveAspectRatio="{par}" href="{uri}"/>'
    )
