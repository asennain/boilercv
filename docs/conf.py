"""Docs config."""

from datetime import date
from hashlib import sha256
from os import environ
from pathlib import Path

from sphinx.application import Sphinx

from boilercv.docs.nbs import DOCS

PACKAGE = "boilercv"
"""Package name."""
STATIC = DOCS / "_static"
"""Static assets folder, used in configs and setup."""
CSS = STATIC / "local.css"
"""Local CSS file, used in configs and setup."""
BIB = DOCS / "refs.bib"
"""Bibliography file."""
REV = (
    Path("../requirements.txt")
    .read_text(encoding="utf-8")
    .splitlines()[1]
    .split("@")[-1]
)
"""Binder revision."""

# ! URLs for autodoc, intersphinx, and tippy
OPENCV = "https://docs.opencv.org/2.4"
NBFORMAT = "https://nbformat.readthedocs.io/en/stable"
NUMPY = "https://numpy.org/doc/stable"
PYQTGRAPH = "https://pyqtgraph.readthedocs.io/en/latest"

# ! Setup


def setup(app: Sphinx):
    """Add functions to Sphinx setup."""
    init_nb_env()
    app.connect("html-page-context", add_version_to_css)


def init_nb_env():
    """Initialize the environment which will be inherited for notebook execution."""
    for key in [
        key
        for key in [
            "PIP_DISABLE_PIP_VERSION_CHECK",
            "PYTHONIOENCODING",
            "PYTHONUTF8",
            "PYTHONWARNDEFAULTENCODING",
            "PYTHONWARNINGS",
        ]
        if environ.get(key) is not None
    ]:
        del environ[key]
    environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"


def add_version_to_css(app: Sphinx, _pagename, _templatename, ctx, _doctree):
    """Add the version number to the local.css file, to bust the cache for changes.

    See: https://github.com/executablebooks/MyST-Parser/blob/978e845543b5bcb7af0ff89cac9f798cb8c16ab3/docs/conf.py#L241-L249
    """
    if app.builder.name != "html":
        return
    css = dpath(CSS)
    if css in ctx.get((k := "css_files"), {}):
        ctx[k][ctx[k].index(css)] = f"{css}?hash={sha256(CSS.read_bytes()).hexdigest()}"


def dpaths(*paths: Path, rel: Path = DOCS) -> list[str]:
    """Get the string-representation of paths relative to docs for Sphinx config.

    Args:
        paths: Paths to convert.
        rel: Relative path to convert to. Defaults to the 'docs' directory.
    """
    return [dpath(path, rel) for path in paths]


def dpath(path: Path, rel: Path = DOCS) -> str:
    """Get the string-representation of a path relative to docs for Sphinx config.

    Args:
        path: Path to convert.
        rel: Relative path to convert to. Defaults to the 'docs' directory.
    """
    return path.relative_to(rel).as_posix()


# ! Basics
project = PACKAGE
copyright = f"{date.today().year}, Blake Naccarato, Kwang Jin Kim"  # noqa: A001
version = "0.0.1"
master_doc = "index"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
extensions = [
    "autodoc2",
    "myst_nb",
    "sphinx_design",
    "sphinx_tippy",
    "sphinx_thebe",
    "sphinx_togglebutton",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinxcontrib.bibtex",
    "sphinxcontrib.mermaid",
]
# ! Theme
html_title = PACKAGE
html_favicon = "_static/favicon.ico"
html_logo = "_static/favicon.ico"
html_static_path = dpaths(STATIC)
html_css_files = dpaths(CSS, rel=STATIC)
html_theme = "sphinx_book_theme"
html_context = {
    # ? MyST elements don't look great with dark mode, but allow dark for accessibility.
    "default_mode": "light"
}
COMMON_OPTIONS = {
    "repository_url": f"https://github.com/blakeNaccarato/{PACKAGE}",
    "path_to_docs": dpath(DOCS),
}
html_theme_options = {
    **COMMON_OPTIONS,
    "repository_branch": "main",
    "show_navbar_depth": 2,
    "show_toc_level": 4,
    "use_download_button": True,
    "use_fullscreen_button": True,
    "use_repository_button": True,
}
# ! MyST
myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "attrs_block",
    "linkify",
    "substitution",
]
myst_heading_anchors = 6
myst_substitutions = {
    "binder": f"[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/blakeNaccarato/{PACKAGE}/{REV}?labpath=docs%2Fexperiments%2Fe230920_subcool%2Ffind_centers.ipynb)"
}
# ! BibTeX
bibtex_bibfiles = dpaths(BIB)
bibtex_reference_style = "label"
bibtex_default_style = "unsrt"
# ! NB
nb_execution_mode = "cache"
nb_execution_raise_on_error = True
# ! Thebe
thebe_config = {**COMMON_OPTIONS, "repository_branch": REV, "selector": "div.highlight"}
# ! Other
math_eqref_format = "Eq. {number}"
mermaid_d3_zoom = False
# ! Autodoc2
nitpicky = True
autodoc2_packages = [f"../src/{PACKAGE}"]
autodoc2_render_plugin = "myst"
# ? Autodoc2 does not currently obey `python_display_short_literal_types` or
# ? `python_use_unqualified_type_names`, but `maximum_signature_line_length` makes it a
# ? bit prettier.
# ? https://github.com/sphinx-extensions2/sphinx-autodoc2/issues/58
maximum_signature_line_length = 88
# ! Intersphinx
intersphinx_mapping = {
    "cv2": (OPENCV, None),
    "nbformat": (NBFORMAT, None),
    "numpy": (NUMPY, None),
    "pyqtgraph": (PYQTGRAPH, None),
    "matplotlib": ("https://matplotlib.org/stable", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "python": ("https://docs.python.org/3", None),
}
nitpick_ignore = [
    ("py:class", "cv2.LineSegmentDetector"),
    ("py:class", "boilercv.correlations.T"),
    ("py:class", "boilercv.data.sets.Stage"),
    ("py:class", "boilercv.experiments.e230920_subcool.NbProcess"),
]
nitpick_ignore_regex = [
    # ? Type aliases
    ("py:.*", r"boilercv\.types\..*"),
    ("py:.*", r"boilercv\.captivate\.previews\..*"),
    # ? Ignore until I'm using autodoc there, too
    ("py:.*", r"boilercore\..*"),
    # ? Typing portion not found
    ("py:.*", r"numpy\.typing\..*"),
    # ? Until we're done with Pydantic v1
    ("py:.*", r"pydantic\.v1\..*"),
    # ? https://bugreports.qt.io/browse/PYSIDE-2215
    ("py:.*", r"PySide6\..*"),
]
# ! Tippy
# ? https://sphinx-tippy.readthedocs.io/en/latest/index.html#confval-tippy_anchor_parent_selector
tippy_anchor_parent_selector = "article.bd-article"
# ? Mermaid tips don't work
tippy_skip_anchor_classes = ["mermaid"]
# ? https://github.com/sphinx-extensions2/sphinx-tippy/issues/6#issuecomment-1627820276
tippy_enable_mathjax = True
tippy_tip_selector = """
    aside,
    div.admonition,
    div.literal-block-wrapper,
    figure,
    img,
    div.math,
    p,
    table
    """
# ? Skip Zenodo DOIs as the hover hint doesn't work properly
tippy_skip_urls = [r"https://doi\.org/10\.5281/zenodo\..+"]
# ? Other
tippy_rtd_urls = [OPENCV, NBFORMAT, NUMPY, PYQTGRAPH]
