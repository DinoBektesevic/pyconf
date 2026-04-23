"""CLI integration helpers for cfx Config classes.

This module is intentionally not part of the public API. Use the classmethods
on `Config` (``add_arguments``, ``from_argparse``, ``click_options``,
``from_click``) instead.

The CLI representation of each field type is now owned by the field itself via
``ConfigField.to_argparse_kwargs`` and ``ConfigField.to_click_option``. This
module only re-exports ``_CLI_UNSET`` for use in ``Config._apply_params``.
"""

from .types.config_field import _CLI_UNSET

__all__ = []  # internal module; nothing exported

# Re-export for Config._apply_params usage.
# Defined in config_field to avoid a circular import (cli.py imports types.py).
_CLI_UNSET = _CLI_UNSET
