"""Sphinx configuration for the ptools documentation."""

from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version

# Make the in-tree source importable so autodoc can find ptools without
# requiring an editable install.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

# -- Project information -----------------------------------------------------

project = "ptools"
author = "Omar Ibrahim"
copyright = "Omar Ibrahim"

try:
    release = _pkg_version("ptools")
except PackageNotFoundError:
    release = "1.0.0"
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_click",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Source files can be either reStructuredText or Markdown.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- autodoc / autosummary ---------------------------------------------------

autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_typehints = "description"
autodoc_member_order = "bysource"

# Some optional third-party deps pulled in by ptools subcommands aren't
# needed to render the docs, mock them so autodoc doesn't fail importing
# modules that reference them at import time.
autodoc_mock_imports = [
    "openai",
    "google",
    "google.generativeai",
    "pygments",
    "textual",
    "prompt_toolkit",
    "Crypto",
    "keyring",
    "lark",
    "watchdog",
    "humanize",
    "numpy",
    "requests",
    "yaml",
    "jinja2",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "click": ("https://click.palletsprojects.com/en/stable/", None),
}

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_title = f"ptools {release}"
