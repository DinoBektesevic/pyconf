"""Formatting helpers for rendering Config instances as text or HTML tables.

This module is intentionally not re-exported from the top-level package.
Import directly when needed::

    from cfx.display import make_table, as_table

Public API
----------
textwrap_cell, textwrap_row
    Text/terminal table cell and row helpers.
wrap_cell, wrap_row
    HTML tag helpers with optional attribute support.
make_table
    Unified table builder - produces either a fixed-width text table or an
    HTML ``<table>`` from a list of ``(config, name, value, doc)`` rows.
as_table
    Full config renderer for ``__str__`` (format ``"text"``) and
    ``_repr_html_`` (format ``"html"``).
as_inline_string
    Compact ``ClassName(k=v, ...)`` one-liner for ``__repr__``.
config_tree
    Tree diagram of a config hierarchy with wrapped docstrings.
table_rows
    Extract ``(field_name, current_value, doc)`` 3-tuples from a flat config.
flat_table_rows
    Extract ``(class_name, field_name, value, doc)`` 4-tuples recursively.
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
    "config_tree",
    "table_rows",
    "flat_table_rows",
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
        Cell strings, one per column.
    max_widths : `tuple[int]`
        Column width limits, one per column.

    Returns
    -------
    wrapped: `list[list[str]]`
        One list-of-lines per column.
    """
    return [
        textwrap_cell(str(row[i]), max_widths[i])
        for i in range(len(max_widths))
    ]


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
            f"{wrapped_cells[col][i] if i < len(wrapped_cells[col]) else '':<{widths[col]}}"  # noqa: E501
            for col in range(len(widths))
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
        3-tuples of ``(key, formatted_value, doc)``.
    """
    rows = []
    for key, value in cfg.items():
        field = getattr(type(cfg), key)
        rows.append((key, field.to_string(value), field.doc))
    return rows


def flat_table_rows(cfg):
    """Extract ``(class_name, key, value, doc)`` tuples from *cfg* recursively.

    Walks *cfg* and all nested sub-configs depth-first, prepending the class
    name as a leading column so all fields across the whole hierarchy can be
    rendered in a single unified table.

    Parameters
    ----------
    cfg : `Config`
        Any `Config` instance, flat or nested.

    Returns
    -------
    rows : `list[tuple]`
        4-tuples of ``(class_name, key, formatted_value, doc)``.
    """
    cls = type(cfg)
    rows = []
    for key, value in cfg.items():
        field = getattr(cls, key)
        rows.append((cls.__name__, key, field.to_string(value), field.doc))
    for confid in getattr(cls, "_nested_classes", {}):
        rows.extend(flat_table_rows(getattr(cfg, confid)))
    return rows


def config_tree(cfg, width=79, _cont="", _branch=""):
    """Render a compact tree diagram of a config hierarchy.

    Each node shows the class name and its docstring (preserved as-is, not
    reflowed). Sub-configs are connected with unicode box-drawing characters.

    Parameters
    ----------
    cfg : `Config`
        Root config instance.
    width : `int`, optional
        Kept for API compatibility; no longer used internally. Default ``79``.
    _cont : `str`
        Internal: continuation prefix for docstring lines and child prefixes.
        Do not pass manually.
    _branch : `str`
        Internal: prefix for this node's first line (e.g. ``"├─ "``).
        Do not pass manually.

    Returns
    -------
    tree : `str`
        Multi-line tree string.
    """
    cls = type(cfg)
    doc = (cls.__doc__ or "").strip()
    nested = list(getattr(cls, "_nested_classes", {}))

    doc_lines = doc.splitlines() if doc else []
    first = f"{_branch}{cls.__name__}"
    if doc_lines:
        first += f": {doc_lines[0]}"
    result = [first]
    for line in doc_lines[1:]:
        result.append(f"{_cont}{line}" if line.strip() else _cont.rstrip())

    for i, confid in enumerate(nested):
        is_last = i == len(nested) - 1
        child_branch = _cont + ("└─ " if is_last else "├─ ")
        child_cont = _cont + ("    " if is_last else "│   ")
        result.append(
            config_tree(getattr(cfg, confid), width, child_cont, child_branch)
        )
    return "\n".join(result)


def make_table(
    rows,
    format="text",
    max_config_width=25,
    max_key_width=20,
    max_value_width=25,
    max_desc_width=50,
    table_attrs=None,
):
    """Format ``(config, name, value, doc)`` rows as a text or HTML table.

    Parameters
    ----------
    rows : `list[tuple]`
        Each tuple is ``(config_class, key, value, description)``.
    format : `str`, optional
        ``"text"`` for a fixed-width terminal table; ``"html"`` for a
        ``<table>`` string. Default ``"text"``.
    max_config_width : `int`, optional
        Max width for the Config column. Ignored in HTML mode.
    max_key_width : `int`, optional
        Max width for the Key column. Ignored in HTML mode.
    max_value_width : `int`, optional
        Max width for the Value column. Ignored in HTML mode.
    max_desc_width : `int`, optional
        Max width for the Description column. Ignored in HTML mode.
    table_attrs : `dict` or `None`, optional
        HTML attributes added to the ``<table>`` tag, e.g.
        ``{"class": "my-table", "id": "pipeline-config"}``.
        Only used when ``format="html"``. Default ``None``.

    Returns
    -------
    table: `str`
        Fixed-width text table or ``<table>...</table>`` HTML string.
    """
    if format == "html":
        header_row = wrap_row(
            [
                wrap_cell("Config", tag="th"),
                wrap_cell("Key", tag="th"),
                wrap_cell("Value", tag="th"),
                wrap_cell("Description", tag="th"),
            ]
        )
        body = "".join(
            wrap_row(
                [
                    wrap_cell(f"<code>{cfg}</code>"),
                    wrap_cell(f"<code>{k}</code>"),
                    wrap_cell(f"<code>{v}</code>"),
                    wrap_cell(d),
                ]
            )
            for cfg, k, v, d in rows
        )
        attr_str = ""
        if table_attrs:
            attr_str = " " + " ".join(
                f'{k}="{v}"' for k, v in table_attrs.items()
            )
        return f"<table{attr_str}>{header_row}{body}</table>"

    # text mode
    header = ("Config", "Key", "Value", "Description")
    max_widths = (
        max_config_width,
        max_key_width,
        max_value_width,
        max_desc_width,
    )
    wrapped_header = textwrap_row(header, max_widths)
    wrapped_rows = [textwrap_row(r, max_widths) for r in rows]
    all_wrapped = [wrapped_header] + wrapped_rows
    widths = [
        max(len(line) for wr in all_wrapped for line in wr[i])
        for i in range(4)
    ]
    sep = "-+-".join("-" * w for w in widths)
    lines = [fmt_text_row(wrapped_header, widths), sep] + [
        fmt_text_row(wr, widths) for wr in wrapped_rows
    ]
    return "\n".join(lines)


def as_table(cfg, format="text", table_attrs=None):
    """Render a `Config` instance as a full text or HTML table.

    Produces a tree diagram of the config hierarchy (with wrapped docstrings)
    followed by a single unified table with a leading Config column. Works for
    flat, nested, and mixed flat+nested configs.

    Parameters
    ----------
    cfg : `Config`
        The config instance to render.
    format : `str`, optional
        ``"text"`` for a terminal table; ``"html"`` for an HTML block.
        Default ``"text"``.
    table_attrs : `dict` or `None`, optional
        HTML attributes for the ``<table>`` tag, e.g.
        ``{"class": "my-table", "id": "pipeline-config"}``.
        Only used when ``format="html"``. Default ``None``.

    Returns
    -------
    table : `str`
        Tree diagram followed by the unified field table.
    """
    rows = flat_table_rows(cfg)

    if format == "html":
        tree_html = f"<pre>{config_tree(cfg)}</pre>"
        return tree_html + make_table(
            rows, format="html", table_attrs=table_attrs
        )  # noqa: E501

    # text mode: compute actual column widths first so the tree can wrap
    # to the same total width as the table.
    max_widths = (25, 20, 25, 50)
    header = ("Config", "Key", "Value", "Description")
    all_wrapped = [textwrap_row(header, max_widths)] + [
        textwrap_row(r, max_widths) for r in rows
    ]
    widths = [
        max(len(line) for wr in all_wrapped for line in wr[i])
        for i in range(4)
    ]
    total_width = sum(widths) + 3 * 3  # 4 cols = 3 separators of " | "
    tree = config_tree(cfg, width=total_width)
    table = make_table(rows, format="text")
    return tree + "\n" + table


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
    parts = [f"{k}={getattr(cfg, k)!r}" for k in cfg]
    parts += [
        f"{c}={as_inline_string(getattr(cfg, c))}" for c in nested_classes
    ]  # noqa: E501
    return f"{type(cfg).__name__}({', '.join(parts)})"
