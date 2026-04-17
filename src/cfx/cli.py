"""CLI integration helpers for cfx Config classes.

This module is intentionally not part of the public API. Use the classmethods
on `Config` (``add_arguments``, ``from_args``, ``from_cli``, ``click_options``,
``from_click``) instead.
"""

import argparse

from .types import (
    Bool, Date, DateTime, Dict, Float, Int, List, MultiOptions,
    Options, Path, Range, Scalar, Seed, Time,
)


__all__ = []   # internal module; nothing exported


def _flag_name(name, prefix):
    """Return the CLI flag string (e.g. ``--search.n-sigma``).

    Parameters
    ----------
    name : `str`
        Field attribute name (underscores allowed).
    prefix : `str`
        Dot-separated prefix for nested configs. Empty string means no prefix.

    Returns
    -------
    flag : `str`
        Option string such as ``"--n-sigma"`` or ``"--search.n-sigma"``.
    """
    hyphenated = name.replace("_", "-")
    if prefix:
        return f"--{prefix}.{hyphenated}"
    return f"--{hyphenated}"


def _dest_name(name, prefix):
    """Return the argparse dest (e.g. ``search.n_sigma``).

    Parameters
    ----------
    name : `str`
        Field attribute name.
    prefix : `str`
        Dot-separated prefix for nested configs.

    Returns
    -------
    dest : `str`
        Destination key used in the parsed namespace dict.
    """
    if prefix:
        return f"{prefix}.{name}"
    return name


def field_to_argparse_kwargs(name, descriptor, prefix=""):
    """Build the keyword-argument dict for ``parser.add_argument()``.

    The returned dict contains a ``"flag"`` key with the full option string
    plus all remaining kwargs for ``parser.add_argument()``. Pull ``"flag"``
    out separately when calling argparse::

        info = field_to_argparse_kwargs(name, descriptor)
        flag = info.pop("flag")
        parser.add_argument(flag, **info)

    Parameters
    ----------
    name : `str`
        Field attribute name on the `Config` class.
    descriptor : `ConfigField`
        The descriptor instance.
    prefix : `str`, optional
        Dot-separated prefix for nested configs (e.g. ``"search"``).
        Default is ``""`` (no prefix).

    Returns
    -------
    kwargs : `dict`
        Always contains ``"flag"``, ``"dest"``, ``"default"``, and ``"help"``.
        Type- or action-specific keys (``"type"``, ``"action"``, ``"choices"``,
        ``"nargs"``, ``"metavar"``) are added as appropriate.
    """
    flag = _flag_name(name, prefix)
    dest = _dest_name(name, prefix)
    kwargs = {"flag": flag, "dest": dest, "default": None, "help": descriptor.doc}

    if isinstance(descriptor, Bool):
        kwargs["action"] = argparse.BooleanOptionalAction
        return kwargs

    if isinstance(descriptor, MultiOptions):
        kwargs["nargs"] = "+"
        kwargs["choices"] = list(descriptor.options)
        kwargs["type"] = str
        return kwargs

    if isinstance(descriptor, Options):
        kwargs["choices"] = list(descriptor.options)
        kwargs["type"] = str
        return kwargs

    if isinstance(descriptor, (Int, Float, Scalar)):
        kwargs["type"] = descriptor.from_string
        return kwargs

    if isinstance(descriptor, Path):
        kwargs["type"] = descriptor.from_string
        kwargs["metavar"] = "PATH"
        return kwargs

    if isinstance(descriptor, Seed):
        kwargs["type"] = descriptor.from_string
        kwargs["metavar"] = "INT|none"
        return kwargs

    if isinstance(descriptor, Range):
        kwargs["type"] = descriptor.from_string
        kwargs["metavar"] = "MIN,MAX"
        return kwargs

    if isinstance(descriptor, List):
        kwargs["nargs"] = "+"
        kwargs["type"] = descriptor.element_type if descriptor.element_type is not None else str
        return kwargs

    if isinstance(descriptor, Dict):
        kwargs["type"] = descriptor.from_string
        kwargs["metavar"] = "JSON"
        return kwargs

    if isinstance(descriptor, DateTime):
        kwargs["type"] = descriptor.from_string
        kwargs["metavar"] = "YYYY-MM-DDTHH:MM:SS"
        return kwargs

    if isinstance(descriptor, Date):
        kwargs["type"] = descriptor.from_string
        kwargs["metavar"] = "YYYY-MM-DD"
        return kwargs

    if isinstance(descriptor, Time):
        kwargs["type"] = descriptor.from_string
        kwargs["metavar"] = "HH:MM:SS"
        return kwargs

    # ConfigField / Any / String / fallback
    kwargs["type"] = str
    return kwargs


def field_to_click_option(name, descriptor, prefix=""):
    """Return a ``click.option()`` decorator for *descriptor*.

    The CLI flag uses dot notation for namespacing (``--search.n-sigma``).
    The click parameter name uses double underscores instead of dots
    (``search__n_sigma``) so it is a valid Python identifier. `from_click`
    reverses this encoding when routing values to the appropriate sub-config.

    Parameters
    ----------
    name : `str`
        Field attribute name on the `Config` class.
    descriptor : `ConfigField`
        The descriptor instance.
    prefix : `str`, optional
        Dot-separated prefix for nested configs (e.g. ``"search"``).
        Default is ``""`` (no prefix).

    Returns
    -------
    decorator : `callable`
        A ``click.option(...)`` decorator ready to be stacked on a command.

    Raises
    ------
    ImportError
        If ``click`` is not installed.
    """
    try:
        import click
    except ImportError:
        raise ImportError(
            "click is required for click_options(). "
            "Install it with: pip install click"
        )

    flag = _flag_name(name, prefix)
    # click param_decls: use double-underscore for dots so the name is a valid
    # Python identifier that click and from_click can both handle.
    param_name = f"{prefix}__{name}" if prefix else name
    base_kw = {"default": None, "help": descriptor.doc, "show_default": False}

    if isinstance(descriptor, Bool):
        hyphenated = name.replace("_", "-")
        if prefix:
            no_flag = f"--{prefix}.no-{hyphenated}"
        else:
            no_flag = f"--no-{hyphenated}"
        return click.option(flag, no_flag, param_name, **base_kw)

    if isinstance(descriptor, MultiOptions):
        return click.option(
            flag, param_name,
            type=click.Choice(list(descriptor.options)),
            multiple=True,
            **base_kw,
        )

    if isinstance(descriptor, Options):
        return click.option(
            flag, param_name,
            type=click.Choice(list(descriptor.options)),
            **base_kw,
        )

    if isinstance(descriptor, (Int, Float, Scalar, Path, Seed, Range, Dict,
                                Date, Time, DateTime)):
        return click.option(flag, param_name, type=descriptor.from_string, **base_kw)

    if isinstance(descriptor, List):
        elem = descriptor.element_type if descriptor.element_type is not None else str
        return click.option(flag, param_name, type=elem, multiple=True, **base_kw)

    # ConfigField / Any / String / fallback
    return click.option(flag, param_name, type=str, **base_kw)
