"""Sphinx configuration for cfx."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

project = "cfx"
author = "Dino Bektesevic"
copyright = f"2026, {author}"

# ---------------------------------------------------------------------------
# Footer icon assets (SVG content read once at build time so the dict stays
# readable; SVG files live in docs/_static/).
# ---------------------------------------------------------------------------
_static = Path(__file__).parent / "_static"
_GITHUB_ICON = (_static / "github.svg").read_text()
_PYPI_ICON = (_static / "pypi.svg").read_text()

extensions = [
    "autoapi.extension",
    "myst_parser",
    "numpydoc",
    "sphinx.ext.doctest",
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

html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "light_logo": "logo/color_large.svg",
    "dark_logo": "logo/darktheme_color_large.svg",
    "sidebar_hide_name": True,
    "source_repository": "https://github.com/DinoBektesevic/cfx/",
    "source_branch": "main",
    "source_directory": "docs/",
    "navigation_with_keys": True,
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/DinoBektesevic/cfx",
            "html": _GITHUB_ICON,
            "class": "",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/cfx/",
            "html": _PYPI_ICON,
            "class": "",
        },
    ],
}

# Don't show typehints in signatures — numpydoc handles them in the body
autodoc_typehints = "none"

default_role = "py:obj"
