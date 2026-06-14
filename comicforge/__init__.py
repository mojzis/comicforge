"""ComicForge — a tiny, scriptable comic page engine.

Write a comic as a YAML spec; render to SVG / PNG / PDF.
Designed so an LLM (or you) can author pages as plain declarative text.
"""
from .render import render_spec, load_spec  # noqa: F401

__version__ = "0.1.0"
