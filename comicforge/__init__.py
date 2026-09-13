"""ComicForge — a tiny, scriptable comic page engine.

Write a comic as a YAML spec; render to SVG / PNG / PDF.
Designed so an LLM (or you) can author pages as plain declarative text.
"""

from .pixelart import PixelLibrary  # noqa: F401
from .render import (  # noqa: F401
    bubble_layout,
    load_spec,
    page_squeeze,
    panel_layout,
    render_scene,
    render_spec,
)

__version__ = "0.2.0"
