"""CLI integration helpers for cfx Config classes.

This module is intentionally not part of the public API. Use the classmethods
on `Config` (``add_arguments``, ``from_argparse``, ``click_options``,
``from_click``) instead.
"""

import argparse

from .types import (
    Bool,
    Date,
    DateTime,
    Dict,
    List,
    MultiOptions,
    Options,
    Path,
    Range,
    Seed,
    Time,
)

try:
    import click
except ImportError:
    click = None


__all__ = []  # internal module; nothing exported

# Sentinel for "this CLI argument was not supplied by the user."
# Using None is wrong because some fields (Seed, Any) legitimately accept None
# as a value. _CLI_UNSET lets _apply_params distinguish "not provided" from
# "explicitly provided as None".
_CLI_UNSET = object()


# Maps field class -> function(descriptor) -> extra kwargs for add_argument.
# Classes absent from this table fall through to from_string + metavar.
# Bool is excluded - it uses action= instead of type= and is handled directly.
_ARGPARSE_SPECIAL = {
    MultiOptions: lambda d: {
        "nargs": "+",
        "choices": list(d.options),
        "type": str,
    },
    Options: lambda d: {
        "choices": list(d.options),
        "type": str,
    },
    List: lambda d: {
        "nargs": "+",
        "type": d.element_type if d.element_type is not None else str,
    },
}

# Maps field class -> metavar string shown in --help output.
_ARGPARSE_METAVAR = {
    Path: "PATH",
    Seed: "INT|none",
    Range: "MIN,MAX",
    Dict: "JSON",
    Date: "YYYY-MM-DD",
    Time: "HH:MM:SS",
    DateTime: "YYYY-MM-DDTHH:MM:SS",
}


def flag_name(name, prefix):
    """Return the CLI flag string (e.g. ``--search.n-sigma``)."""
    hyphenated = name.replace("_", "-")
    if prefix:
        return f"--{prefix}.{hyphenated}"
    return f"--{hyphenated}"


def dest_name(name, prefix):
    """Return the argparse dest (e.g. ``search.n_sigma``)."""
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
    kwargs = {
        "flag": flag_name(name, prefix),
        "dest": dest_name(name, prefix),
        "default": _CLI_UNSET,
        "help": descriptor.doc,
    }

    if isinstance(descriptor, Bool):
        kwargs["action"] = argparse.BooleanOptionalAction
        return kwargs

    extra_fn = _ARGPARSE_SPECIAL.get(type(descriptor))
    if extra_fn is not None:
        kwargs.update(extra_fn(descriptor))
        return kwargs

    # General case: use from_string as the argparse type= callable,
    # plus an optional metavar for fields with a non-obvious string format.
    kwargs["type"] = descriptor.from_string
    metavar = _ARGPARSE_METAVAR.get(type(descriptor))
    if metavar is not None:
        kwargs["metavar"] = metavar
    return kwargs


# Maps field class -> function(descriptor) -> extra kwargs for click.option.
# Bool and classes absent from this table are handled separately.
def click_special(descriptor):  # noqa: E302
    """Return extra click.option kwargs for types needing special handling."""
    cls = type(descriptor)
    if cls is MultiOptions:
        return {
            "type": click.Choice(list(descriptor.options)),
            "multiple": True,
        }
    if cls is Options:
        return {"type": click.Choice(list(descriptor.options))}
    if cls is List:
        et = descriptor.element_type
        return {"type": et if et is not None else str, "multiple": True}
    return None


def field_to_click_option(name, descriptor, prefix=""):
    """Return a ``click.option()`` decorator for *descriptor*.

    The CLI flag uses dot notation for namespacing (``--search.n-sigma``).
    The click parameter name uses double underscores instead of dots
    (``search__n_sigma``) so it is a valid Python identifier. `fromclick`
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
    if click is None:
        raise ImportError(
            "click is required for click_options(). "
            "Install it with: pip install click"
        )

    flag = flag_name(name, prefix)
    param_name = f"{prefix.replace('.', '__')}__{name}" if prefix else name
    base_kw = {"default": None, "help": descriptor.doc, "show_default": False}

    if isinstance(descriptor, Bool):
        hyphenated = name.replace("_", "-")
        if prefix:
            flag_pair = f"--{prefix}.{hyphenated}/--{prefix}.no-{hyphenated}"
        else:
            flag_pair = f"--{hyphenated}/--no-{hyphenated}"
        return click.option(flag_pair, param_name, **base_kw)

    extra = click_special(descriptor)
    if extra is not None:
        return click.option(flag, param_name, **extra, **base_kw)

    # General case: use from_string as the click type= callable.
    return click.option(
        flag, param_name, type=descriptor.from_string, **base_kw
    )
