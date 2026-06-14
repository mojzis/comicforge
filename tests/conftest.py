from pathlib import Path

import pytest

from comicforge.library import Library
from comicforge.pixelart import PixelLibrary
from comicforge.render import load_spec
from comicforge.scene import SceneLibrary

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def library():
    return Library(ROOT / "library" / "characters")


@pytest.fixture
def scenes():
    return SceneLibrary(ROOT / "projects" / "_scenes")


@pytest.fixture
def pixel():
    return PixelLibrary(ROOT / "library" / "pixel")


@pytest.fixture
def illustration_spec():
    return load_spec(ROOT / "projects" / "dvur-scene" / "scene.yaml")


@pytest.fixture(params=["slepice", "kosticka"])
def example_spec(request):
    return load_spec(ROOT / "projects" / request.param / "page.yaml")
