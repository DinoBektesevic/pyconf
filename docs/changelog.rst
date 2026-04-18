Changelog
=========

cfx 0.1.0 (2026-04-17)
-----------------------

Features
^^^^^^^^

- Every :class:`~cfx.Config` subclass now exposes ``add_arguments`` and
  ``from_argparse`` for argparse, plus ``click_options`` and ``from_click``
  for Click (optional dependency).  Nested sub-configs use dot-notation flags
  (e.g. ``--search.n-sigma``), including arbitrarily deep nesting (e.g.
  ``--middle.inner.x``).  An optional config-file positional argument is
  registered automatically - YAML or TOML files are loaded first and CLI
  flags are applied on top.
- Nested container configs can now declare their own flat fields alongside
  sub-configs.  Previously, any flat field on a ``method="nested"`` class was
  silently discarded.  Serialization (``to_dict``, ``from_dict``, YAML,
  TOML), display (``str``, ``repr``, HTML), equality, ``__contains__``, and
  CLI flags all handle the mixed case correctly.  Expected dict shape:
  ``{"top_field": 99.0, "inner": {"x": 1.0}}``.
- Improved ``config_tree`` display: unicode box-drawing characters
  (``├─``, ``└─``, ``│``) replace the old ``- `` bullets, multiline
  docstrings are preserved exactly as written rather than reflowed, and
  nesting depth is shown via 4-space continuation indents.  The Config column
  cap in ``make_table`` was raised from 15 to 25 characters so class names
  are never broken mid-word.

Internal
^^^^^^^^

- Added GitHub Actions CI running pytest and flake8 across Python 3.11–3.14
  on Ubuntu, Windows, and macOS.  Added a monthly canary workflow against
  Python pre-releases.  Docs are built and hosted automatically by Read the
  Docs on every push to ``main`` and on version tags.
- Renamed internal ``_from_env_str`` to the public ``from_string`` on all
  :class:`~cfx.ConfigField` subclasses.  Added symmetric ``to_string`` for
  display.  The display table now renders ``Path``, ``Dict``, ``Date``,
  ``Time``, ``DateTime``, and ``MultiOptions`` values cleanly instead of
  using raw ``repr``.
- Renamed internal class attribute ``defaults`` to ``_fields`` for clarity.
  ``_fields`` holds flat :class:`~cfx.ConfigField` descriptors;
  ``_nested_classes`` holds component classes.  The underscore prefix on both
  makes the symmetry explicit.
- Type coercions moved into :meth:`~cfx.ConfigField.__set__`: ``List``
  coerces tuples to lists, ``MultiOptions`` coerces lists and tuples to sets.
  This removes ad-hoc coercion from ``from_argparse`` and ``from_click`` and
  ensures consistent behaviour regardless of how a value is assigned.
