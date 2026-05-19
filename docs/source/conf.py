"""Sphinx configuration for Mnemonic documentation."""

import os
import sys

# Add the backend source directory to path
sys.path.insert(0, os.path.abspath("../../backend/src"))

project = "Mnemonic"
copyright = "2024, Mnemonic Contributors"
author = "Mnemonic Contributors"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

html_theme_options = {
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_host": "github",
    "vcs_use_github": True,
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
}

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "show-inheritance": True,
}
