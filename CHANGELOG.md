# cfx 0.2.1 (2026-04-17)

## Bug Fixes

- Composing two components with the same ``confid`` now raises ``ValueError``
  at class-definition time instead of silently dropping the first component.
- ``Int`` and ``Float`` fields now reject ``bool`` values. Previously
  ``True``/``False`` were silently accepted as ``1``/``0`` because ``bool``
  is a subclass of ``int`` in Python. This was inconsistent with ``Bool``,
  which explicitly rejects integers.
- ``Path.validate()`` now raises ``TypeError`` for non-``Path`` values instead
  of silently returning. ``Path.__init__`` also now normalizes string defaults
  to ``pathlib.Path`` at field-definition time, consistent with the pattern
  described for custom fields.
- ``cfg["confid"]`` now returns the nested sub-config object, fixing a broken
  dict-like contract where ``"source" in cfg`` could be ``True`` but
  ``cfg["source"]`` raised ``KeyError``.

## Documentation

- Documentation improvements: added sharp-edges entries for TOML dropping
  ``None`` values and ``List.from_string`` silent JSON fallback; documented
  ``validate()`` call timing; added ``Options``/``MultiOptions`` parameter
  order note; added "which mode to use" guidance to composition page; added
  intro sentences to serialization, using, sharp-edges, and CLI pages; added
  YAML output example and CLI dot-notation mapping table. Landing page title
  and subtitle styling added via ``custom.css``.

## Internal

- Added ``tests/test_display.py`` covering the display module, plus regression
  tests for the four bug fixes and env-var precedence, nested file loading,
  and ``_repr_html_``.


# cfx 0.2.0 (2026-04-17)

## Features

- Improved ``config_tree`` in ``display.py``: replaced ``textwrap.fill``
  with unicode box-drawing characters (``├─``, ``└─``, ``│``). Multiline
  docstrings are now preserved exactly as written rather than reflowed into
  a single paragraph. Nesting depth is indicated by a 4-space continuation
  indent per level. The Config column cap in ``make_table`` was raised from
  15 to 25 characters so that class names are never broken mid-word.
- ``make_table`` and ``as_table`` now accept a ``table_attrs`` keyword argument
  that adds HTML attributes (e.g. ``class``, ``id``) to the generated
  ``<table>`` element, making it straightforward to target the output with
  custom CSS.

## Documentation

- Switched documentation theme from Alabaster to Furo with light and dark
  mode logos, GitHub and PyPI footer icons, and sidebar sections (User Guide,
  API Reference, Development). Updated the canonical example throughout to
  showcase flat fields alongside deep nested sub-configs. Added a Changelog
  page. Removed redundant per-page ``.. contents::`` directives that conflicted
  with Furo's built-in sidebar navigation.


# cfx 0.1.0 (2026-04-17)

## Features

- Every `Config` subclass now exposes `add_arguments` and `from_argparse` for
  argparse, plus `click_options` and `from_click` for click (optional dependency).
  Nested sub-configs use dot-notation flags (e.g. `--search.n-sigma`), including
  arbitrarily deep nesting (e.g. `--middle.inner.x`). An optional config-file
  positional argument is registered automatically — YAML or TOML files are loaded
  first and CLI flags are applied on top.
- Nested container configs can now declare their own flat fields alongside
  sub-configs. Previously, any flat field on a `method="nested"` class was
  silently discarded. Serialization (`to_dict`, `from_dict`, YAML, TOML),
  display (`str`, `repr`, HTML), equality, `__contains__`, and CLI flags all
  handle the mixed case correctly. Expected dict shape:
  `{"top_field": 99.0, "inner": {"x": 1.0}}`.

## Internal

- Added GitHub Actions CI running pytest and flake8 across Python 3.11–3.14 on
  Ubuntu, Windows, and macOS. Added a monthly canary workflow against Python
  pre-releases. Docs are built and hosted automatically by Read the Docs on every
  push to main and on version tags.
- Renamed internal `_from_env_str` to the public `from_string` on all
  `ConfigField` subclasses. Added symmetric `to_string` for display. The display
  table now renders `Path`, `Dict`, `Date`, `Time`, `DateTime`, and `MultiOptions`
  values cleanly instead of using raw `repr`.
- Renamed internal class attribute `defaults` to `_fields` for clarity.
  `_fields` holds flat `ConfigField` descriptors; `_nested_classes` holds
  component classes. The underscore prefix on both makes the symmetry explicit.
- Type coercions moved into `ConfigField.__set__`: `List` coerces tuples to
  lists, `MultiOptions` coerces lists and tuples to sets. This removes ad-hoc
  coercion from `from_argparse` and `from_click` and ensures consistent
  behaviour regardless of how a value is assigned.
