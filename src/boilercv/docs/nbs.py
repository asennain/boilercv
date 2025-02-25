"""Documentation utilities."""

import io
import os
import re
from collections.abc import Callable
from contextlib import contextmanager, nullcontext, redirect_stdout
from dataclasses import dataclass
from os import chdir, environ
from pathlib import Path
from shutil import copy, copytree
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import Any
from warnings import catch_warnings, filterwarnings

from boilercore import WarningFilter, filter_certain_warnings
from IPython.display import HTML, display  # type: ignore
from IPython.utils.capture import capture_output
from matplotlib.pyplot import style
from myst_parser.parsers.docutils_ import cli_html
from numpy import set_printoptions
from pandas import DataFrame, Index, MultiIndex, Series, concat, options
from seaborn import set_theme

import boilercv
from boilercv.types import DfOrS

DOCS = Path("docs")
"""Docs directory."""
DEPS = Path("tests/root")
"""Dependencies shared with tests."""
FONT_SCALE = 1.3
"""Plot font scale."""
PRECISION = 4
"""The desired precision."""
FLOAT_SPEC = f"#.{PRECISION}g"
"""The desired float specification for formatted output."""
HIDE = display()
"""Hide unsuppressed output. Can't use semicolon due to black autoformatter."""
DISPLAY_ROWS = 20
"""The number of rows to display in a dataframe."""


@dataclass
class Paths:
    root: Path
    docs: Path
    deps: Path


def init(font_scale: float = FONT_SCALE) -> Paths:
    """Initialize a documentation notebook."""
    # sourcery skip: extract-method
    filter_certain_warnings(
        package=boilercv,
        other_action="ignore",
        other_warnings=[
            WarningFilter(
                category=FutureWarning,
                message=r"A grouping was used that is not in the columns of the DataFrame and so was excluded from the result\. This grouping will be included in a future version of pandas\. Add the grouping as a column of the DataFrame to silence this warning\.",
            ),
            WarningFilter(
                category=RuntimeWarning, message=r"invalid value encountered in power"
            ),
            WarningFilter(
                category=RuntimeWarning,
                message=r"numpy\.ndarray size changed, may indicate binary incompatibility\. Expected \d+ from C header, got \d+ from PyObject",
            ),
            WarningFilter(
                category=UserWarning,
                message=r"The palette list has more values \(\d+\) than needed \(\d+\), which may not be intended\.",
            ),
            WarningFilter(
                category=UserWarning,
                message=r"To output multiple subplots, the figure containing the passed axes is being cleared\.",
            ),
        ],
    )
    path = Path().cwd()
    was_already_at_root = is_root(path)
    while not is_root(path):
        if path == (path := path.parent):
            raise RuntimeError("Either documentation or dependencies are missing.")
    paths = Paths(*[p.resolve() for p in (path, path / DOCS, path / DEPS)])
    if _in_binder := environ.get("BINDER_LAUNCH_HOST", False):
        copy_deps(paths.deps, paths.root)
    if any((
        _in_ci := environ.get("CI", False),
        _in_dev := was_already_at_root,
        _in_local_docs := not was_already_at_root,
    )):
        copy_deps(paths.deps, paths.docs)
    else:
        raise RuntimeError("Can't determine notebook environment.")
    set_display_options(font_scale)
    return paths


def is_root(path: Path) -> bool:
    """Check if the path is the root of the project."""
    return (path / DOCS).exists() and (path / DEPS).exists()


def copy_deps(src, dst):
    """Copy dependencies to the destination directory."""
    chdir(dst)
    copy(src / "params.yaml", dst)
    copytree(src / "data", dst / "data", dirs_exist_ok=True)


def set_display_options(font_scale):
    # The triple curly braces in the f-string allows the format function to be
    # dynamically specified by a given float specification. The intent is clearer this
    # way, and may be extended in the future by making `float_spec` a parameter.
    options.display.float_format = f"{{:{FLOAT_SPEC}}}".format
    options.display.min_rows = options.display.max_rows = DISPLAY_ROWS
    set_printoptions(precision=PRECISION)
    set_theme(
        context="notebook",
        style="whitegrid",
        palette="deep",
        font="sans-serif",
        font_scale=font_scale,
    )
    style.use("data/plotting/base.mplstyle")


@contextmanager
def nowarn(capture: bool = False):
    """Don't raise any warnings. Optionally capture output for pesky warnings."""
    with catch_warnings(), capture_output() if capture else nullcontext():
        filterwarnings("ignore")
        yield


def keep_viewer_in_scope():
    """Keep the image viewer in scope so it doesn't get garbage collected."""

    from boilercv.captivate.previews import image_viewer  # noqa: PLC0415

    with image_viewer([]) as viewer:
        return viewer


# * -------------------------------------------------------------------------------- * #
# * Render Math in DataFrames locally and in generated docs
# * https://github.com/executablebooks/jupyter-book/issues/1501#issuecomment-1721378476


def display_dataframe_with_math(df, raw=False):
    """Display a dataframe with MathJax-rendered math."""
    html = df.to_html()
    raw_html = re.sub(r"\$.*?\$", lambda m: convert_tex_to_html(m[0], raw=True), html)  # type: ignore
    return raw_html if raw else HTML(raw_html)


def convert_tex_to_html(html, raw=False):
    """Manually apply the MyST parser to convert $-$ into MathJax's HTML code."""
    frontmatter = """
    ---
    myst:
      enable_extensions: [dollarmath, amsmath]
    ---
    """
    with NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write(dedent(frontmatter).strip())
        f.write("\n\n")
        f.write(html)
    with redirect_stdout(io.StringIO()) as sf:
        cli_html([f.name])
    fullhtml = sf.getvalue()  # Returns a large-ish HTML with the full styling header
    os.remove(f.name)  # noqa: PTH107
    # Strip HTML headers to keep only the body with converted math
    m = re.search(r'<body>\n<div class="document">([\s\S]*)</div>\n</body>', fullhtml)
    raw_html = m[1].strip()  # type: ignore
    # Special case: if we provided a snippet with no HTML markup at all, don't wrap the result
    # in <p> tags
    if (
        "\n" not in html
        and "<" not in html
        and (m := re.match(r"<p>(.*)</p>", raw_html))
    ):
        raw_html = m[1]
    # Manually display the result as HTML
    return raw_html if raw else HTML(raw_html)


# * -------------------------------------------------------------------------------- * #
# * Make styled dataframes resepct precision
# * https://gist.github.com/blakeNaccarato/3c751f0a9f0f5143f3cffc525e5dd577


@contextmanager
def style_df(df: DfOrS, head: bool = False):
    """Style a dataframe."""
    df, truncated = truncate(df, head)
    styler = df.style
    yield styler
    display(styler.format(get_df_formatter(df, truncated)))  # type: ignore  # pyright 1.1.333


def display_dfs(*dfs: DfOrS, head: bool = False):
    """Display formatted DataFrames.

    When a mapping of column names to callables is given to the Pandas styler, the
    callable will be used internally by Pandas to produce formatted strings. This
    differs from elementwise formatting, in which Pandas expects the callable to
    actually process the value and return the formatted string.
    """
    for df in dfs:
        df, truncated = truncate(df, head)
        display(df.style.format(get_df_formatter(df, truncated)))  # type: ignore  # pyright 1.1.333


def get_df_formatter(
    df: DataFrame, truncated: bool
) -> Callable[..., str] | dict[str, Callable[..., str]]:
    """Get formatter for the dataframe."""
    if truncated:
        return format_cell
    cols = df.columns
    types = {col: dtype.type for col, dtype in zip(cols, df.dtypes, strict=True)}
    return {col: get_formatter(types[col]()) for col in cols}


def format_cell(cell) -> str:
    """Format individual cells."""
    return get_formatter(cell)(cell)


def get_formatter(instance: Any) -> Callable[..., str]:
    """Get the formatter depending on the type of the instance."""
    match instance:
        case float():
            return lambda cell: f"{cell:{FLOAT_SPEC}}"
        case _:
            return lambda cell: f"{cell}"


def truncate(df: DfOrS, head: bool = False) -> tuple[DataFrame, bool]:
    """Truncate long dataframes, showing only the head and tail."""
    if isinstance(df, Series):
        df = df.to_frame()
    if len(df) <= options.display.max_rows:
        return df, False
    if head:
        return df.head(options.display.min_rows), True
    df = df.copy()
    # Resolves case when column names are not strings for latter assignment, e.g. when
    # the column axis is a RangeIndex.
    df.columns = [str(col) for col in df.columns]
    # Resolves ValueError: Length of names must match number of levels in MultiIndex.
    ellipsis_index = ("...",) * df.index.nlevels
    df = concat([
        df.head(options.display.min_rows // 2),
        df.iloc[[0]]  # Resolves ValueError: cannot handle a non-unique multi-index!
        .reindex(
            MultiIndex.from_tuples([ellipsis_index], names=df.index.names)
            if isinstance(df.index, MultiIndex)
            else Index(ellipsis_index, name=df.index.name)
        )
        .assign(**dict.fromkeys(df.columns, "...")),
        df.tail(options.display.min_rows // 2),
    ])
    return df, True
