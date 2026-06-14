from pathlib import Path

import pytest

from comicforge.library import Library
from comicforge.pixelart import PixelLibrary
from comicforge.render import load_spec
from comicforge.scene import SceneLibrary

ROOT = Path(__file__).resolve().parent.parent
PES = ROOT / "examples" / "pes"


@pytest.fixture
def library():
    return Library(PES / "characters")


@pytest.fixture
def scenes():
    return SceneLibrary(PES / "scenes")


@pytest.fixture
def pixel():
    return PixelLibrary(PES / "pixel")


@pytest.fixture
def illustration_spec():
    return load_spec(PES / "pages" / "dvur-scene.yaml")


@pytest.fixture(params=["slepice", "kosticka"])
def example_spec(request):
    return load_spec(PES / "pages" / f"{request.param}.yaml")
