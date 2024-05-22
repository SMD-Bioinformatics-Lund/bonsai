# Configuration file for the Sphinx documentation builder.
import pathlib
import sys

# add apps to PATH
apps = ["frontend", "api", "minhash_service", "allele_cluster_service"]
base_dir = pathlib.Path.cwd().parent.parent
for app in apps:
    sys.path.insert(0, str(base_dir.joinpath(app)))

# -- Project information
project = "Bonsai"
author = "Markus Johansson"
copyright = "Region Skåne"

release = "0.1"
version = "0.1.0"

# -- General configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.graphviz",
    "sphinx.ext.napoleon",
    "myst_parser",
]
autosummary_generate = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]

templates_path = ["_templates"]

# -- Options for HTML output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_logo = "img/logo.png"
html_theme_options = {
    "logo_only": True,
}

# -- Options for EPUB output
epub_show_urls = "footnote"

language = "en"
