"""Verify that the installed scaffold is importable."""

from importlib import import_module
from importlib.metadata import metadata
from pkgutil import walk_packages

import fantasy_gm


def test_installed_package_imports() -> None:
    assert metadata("fantasy-gm")["Name"] == "fantasy-gm"
    for module in walk_packages(fantasy_gm.__path__, prefix="fantasy_gm."):
        import_module(module.name)
