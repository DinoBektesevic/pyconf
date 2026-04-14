"""Sphinx configuration for pyconf."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

project = "pyconf"
author = "Dino Bektesevic"
copyright = f"2026, {author}"

extensions = [
    "autoapi.extension",
    "numpydoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

# sphinx-autoapi: point at src/, let it discover everything
autoapi_dirs = ["../src"]
autoapi_type = "python"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]
autoapi_keep_files = False
autoapi_root = "api"
autoapi_ignore = ["*/.#*", "*~", "#*#"]

# numpydoc
numpydoc_show_class_members = True
numpydoc_class_members_toctree = False

# intersphinx: link to Python stdlib docs
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 3,
    "titles_only": False,
}

# Don't show typehints in signatures — numpydoc handles them in the body
autodoc_typehints = "none"

default_role = "py:obj"
