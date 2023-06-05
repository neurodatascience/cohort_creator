# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
from __future__ import annotations

from cohort_creator._version import __version__

# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__


project = "cohort creator"
copyright = "2023, Rémi Gau"
author = "Rémi Gau"


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx_copybutton",
    "myst_parser",
    "sphinxarg.ext",
]

templates_path = ["_templates"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"


# Configuration of sphinx.ext.coverage
coverage_show_missing_items = True
