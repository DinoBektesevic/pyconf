"""Formatting helpers for rendering Config instances as text or HTML tables.

This module is intentionally not re-exported from the top-level package.
Import directly when needed::

    from pyconf.display import make_table, wrap_cell

Public API
----------
textwrap_cell, textwrap_row
    Text/terminal table cell and row helpers.
wrap_cell, wrap_row
    HTML tag helpers with optional attribute support.
make_table
    Unified table builder - produces either a fixed-width text table or an
    HTML ``<table>`` from a list of ``(name, value, doc)`` rows.
as_table
    Full config renderer for ``__str__`` (format ``"text"``) and
    ``_repr_html_`` (format ``"html"``).
as_inline_string
    Compact ``ClassName(k=v, ...)`` one-liner for ``__repr__``.
"""

import textwrap

__all__ = [
    "textwrap_cell",
    "textwrap_row",
    "wrap_cell",
    "wrap_row",
    "make_table",
    "as_table",
    "as_inline_string",
]


def textwrap_cell(text, max_w):
    r"""Reformat a paragraph to fit into no more than ``max_w`` columns.

    By default, tabs in 'text' are expanded with string.expandtabs(), and all
    other whitespace characters (including newline) are converted to space. An
    empty string produces a single-element list ``[""]`` so that callers never
    receive an empty list.

    Parameters
    ----------
    text : `str`
        Cell content to wrap.
    max_w : `int`
        Maximum line width in characters.

    Returns
    -------
    wrapped : `list[str]`
    """
    lines = textwrap.wrap(str(text), max_w)
    return lines if lines else [""]


def textwrap_row(row, max_widths):
    """Given a list of paragraphs, wraps each paragraph at max_widths columns.

    Parameters
    ----------
    row : `tuple[str]`
        ``(key, value, description)`` strings.
    max_widths : `tuple[int]`
        ``(max_key_w, max_value_w, max_desc_w)`` column limits.

    Returns
    -------
    wrapped: `list[list[str]]`
        One list-of-lines per column.
    """
    return [textwrap_cell(str(row[i]), max_widths[i])
            for i in range(len(max_widths))]


def wrap_cell(content, tag="td", attrs=None):
    """Wrap content in an HTML tag.

    Given a string and a tag, returns <tag> content </tag>. The attributes,
    when provided, are unrolled as html tag attributes, f.e.:
    <tag id=1> content </tag>

    Parameters
    ----------
    content : `str`
        Inner HTML content.
    tag : `str`, optional
        HTML element name. Default ``"td"``.
    attrs : `dict` or `None`, optional
        Mapping of attribute name to value appended to the opening tag,
        e.g. ``{"class": "cfg-key", "id": "n_sigma"}``.

    Returns
    -------
    wrapped: `str`
        String of the format: ``<tag [attrs]>content</tag>``.
    """
    attr_str = ""
    if attrs:
        attr_str = " " + " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"<{tag}{attr_str}>{content}</{tag}>"


def wrap_row(cells, tag="tr", attrs=None):
    """Wrap a list of strings in an HTML tag.

    Parameters
    ----------
    cells : `iterable[str]`
        Cell HTML strings to concatenate inside the row.
    tag : `str`, optional
        HTML element name. Default ``"tr"``.
    attrs : `dict` or `None`, optional
        Mapping of attribute name to value, e.g. ``{"class": "cfg-row"}``.

    Returns
    -------
    wrapped: `str`
        String of the format: ``<tag [attrs]> cells... </tag>``.
    """
    attr_str = ""
    if attrs:
        attr_str = " " + " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"<{tag}{attr_str}>{''.join(cells)}</{tag}>"


def fmt_text_row(wrapped_cells, widths):
    r"""Format a single row into a fixed-width string.

    A single row is an iterable. Each element of a row represents unit of
    content that is separated from neighboring content by a ``" | "``.
    The content itself is an iterable such that it spans multiple text-rows,
    for example:

        | content | content |
        |         | content |


    Parameters
    ----------
    wrapped_cells : `list[list[str]]`
        One list-of-lines per column, as returned by `textwrap_row`.
    widths : `list[int]`
        Actual column widths (used for left-justifying each line).

    Returns
    -------
    textrow : `str`
        One or more lines joined by ``"\\n"``.
    """
    n = max(len(c) for c in wrapped_cells)
    out = []
    for i in range(n):
        parts = [
            (wrapped_cells[col][i] if i < len(wrapped_cells[col]) else "").ljust(widths[col])  # noqa: E501
            for col in range(3)
        ]
        out.append(" | ".join(parts))
    return "\n".join(out)


#############################################################################
#                            Printers
#############################################################################

def table_rows(cfg):
    """Extract ``(field_name, current_value, doc)`` tuples from *cfg*.

    Parameters
    ----------
    cfg : `Config`
        Any `Config` instance.

    Returns
    -------
    rows: `list[tuple]`
    """
    rows = []
    for key, value in cfg.items():
        # to_string is a staticmethod defined on ConfigField so just fetch it
        field = getattr(type(cfg), key)
        fmtstr = field.to_string(value)
        rows.append((key, fmtstr, field.doc))
    return rows


def make_table(rows, format="text", max_key_width=20, max_value_width=25,
               max_desc_width=50):
    """Format ``(name, value, doc)`` rows as a text or HTML table.

    Parameters
    ----------
    rows : `list[tuple]`
        Each tuple format is ``(key, value, description)``.
    format : `str`, optional
        If format is "text", returns a markdown-like table. If the format is
        "html", returns a string HTML table. Default "text".
    max_key_width : `int`, optional
        Max width for the first column, represents "Key". Ignored in HTML mode.
    max_value_width : `int`, optional
        Max width for the second column, represents the value of a config
        field. Ignored in HTML mode.
    max_desc_width : `int`, optional
        Max width for the third column, represents the doc string of a config
        field. Ignored in HTML mode.

    Returns
    -------
    table: `str`
        Fixed-width text table or ``<table>...</table>`` HTML string.
    """
    if format == "html":
        header_row = wrap_row([
            wrap_cell("Key",         tag="th"),
            wrap_cell("Value",       tag="th"),
            wrap_cell("Description", tag="th"),
        ])
        body = "".join(
            wrap_row([
                wrap_cell(f"<code>{k}</code>"),
                wrap_cell(f"<code>{v}</code>"),
                wrap_cell(d),
            ])
            for k, v, d in rows
        )
        return f"<table>{header_row}{body}</table>"

    # text mode
    header = ("Key", "Value", "Description")
    max_widths = (max_key_width, max_value_width, max_desc_width)
    wrapped_header = textwrap_row(header, max_widths)
    wrapped_rows = [textwrap_row(r, max_widths) for r in rows]
    all_wrapped = [wrapped_header] + wrapped_rows
    widths = [
        max(len(line) for wr in all_wrapped for line in wr[i])
        for i in range(3)
    ]
    sep = "-+-".join("-" * w for w in widths)
    lines = [fmt_text_row(wrapped_header, widths), sep] + [
        fmt_text_row(wr, widths) for wr in wrapped_rows
    ]
    return "\n".join(lines)


def as_table(cfg, format="text"):
    """Render a `Config` instance as a full text or HTML table.

    Handles both flat configs (fields rendered as rows) and nested configs
    (sub-configs rendered recursively).

    Parameters
    ----------
    cfg : `Config`
        The config instance to render.
    format : `str`, optional
        When "text" renders a markdown-style table as a string, when "html"
        renders ``<table>...</table>`` HTML string. Default: text.

    Returns
    -------
    table : `str`
        Complete rendered representation including title and docstring.
    """
    nested_classes = getattr(type(cfg), "_nested_classes", {})
    title = type(cfg).__name__
    doc = type(cfg).__doc__

    if format == "html":
        doc_html = f"<p>{doc.strip()}</p>" if doc else ""
        parts = []
        if cfg._fields:
            parts.append(make_table(table_rows(cfg), format="html"))
        for confid in nested_classes:
            parts.append(as_table(getattr(cfg, confid), format="html"))
        return f"<b>{title}</b>{doc_html}" + "".join(parts)

    # text mode
    header = f"{title}:"
    if doc:
        header += f"\n{doc.strip()}"
    parts = []
    if cfg._fields:
        parts.append(make_table(table_rows(cfg), format="text"))
    for confid in nested_classes:
        parts.append(f"[{confid}]\n{as_table(getattr(cfg, confid), format='text')}")
    return header + "\n" + "\n\n".join(parts)


def as_inline_string(cfg):
    """Render a `Config` instance as a compact ``ClassName(k=v, ...)`` string.

    Parameters
    ----------
    cfg : `Config`
        The config instance to render.

    Returns
    -------
    cfgstr : `str`
        Single-line representation of a config.
    """
    nested_classes = getattr(type(cfg), "_nested_classes", {})
    parts = [f"{k}={getattr(cfg, k)!r}" for k in cfg.keys()]
    parts += [f"{c}={as_inline_string(getattr(cfg, c))}" for c in nested_classes]
    return f"{type(cfg).__name__}({', '.join(parts)})"
