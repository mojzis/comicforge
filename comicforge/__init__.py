"""ComicForge — a tiny, scriptable comic page engine.

Write a comic as a YAML spec; render to SVG / PNG / PDF.
Designed so an LLM (or you) can author pages as plain declarative text.
"""

from .pixelart import PixelLibrary  # noqa: F401
from .render import load_spec, render_scene, render_spec  # noqa: F401

__version__ = "0.1.0"
