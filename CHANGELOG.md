# cfx 0.5.0 (unreleased)

## Features

- `AliasedView`: a self-contained view that auto-generates prefixed `Alias`
  descriptors for every field in each declared component.  Pass
  ``components=[...]`` and optionally ``aliases=[...]`` to override the
  prefix per component (``None`` gives a flat, unprefixed name).  Name
  conflicts raise ``ValueError`` at class-definition time.
- `FlatView`: an ``AliasedView`` with all prefixes set to ``None`` —
  every component field is exposed directly by name.  Raises on conflicts.
- `Mirror`: a config descriptor that keeps two or more dotpaths in sync.
  Declaring `shared = Mirror("a.x", "b.x")` on a `Config` fans writes to
  every path and asserts agreement on read, raising `ValueError` with a
  diff if the paths disagree.  Accepts `FieldRef` objects or plain dotpath
  strings.
- `FieldRef`: accessing a field or component on a `Config` *class* (rather
  than an instance) now returns a `FieldRef` path proxy instead of the raw
  descriptor. `FieldRef` objects chain attribute access to build validated
  dotpath strings and are the preferred input to `Alias` and `Mirror` — pass
  `Alias(SomeConfig.component.field)` instead of `Alias("component.field")`
  to keep paths refactorable via IDE rename and go-to-definition.
- `ComponentRef`: each component slot on a `Config` class now has a
  descriptor installed automatically, so `SomeConfig.component` returns a
  `FieldRef` that can be chained (`SomeConfig.component.field`). Instance
  access is unchanged.

## Internal

- `ConfigMeta` renamed to `_ConfigType` to signal that it is not part of the
  public API and will be replaced by `__init_subclass__` in a future release.
- Internal `getattr(cls, field_name)` call sites in `config.py` and
  `display.py` that previously relied on `ConfigField.__get__` returning the
  descriptor on class access have been updated to use `cls._fields[name]`
  directly.

# cfx 0.4.0 (unreleased)

## Removals
- `method="unroll"` composition mode removed. Defining a class with
  `method="unroll"` now raises `TypeError` at class-definition time. Use
  nested composition (the default when `components=` is provided) instead.

## Bug Fixes
- `diff()` now recurses into nested sub-configs. Differences in nested fields
  appear with dot-notation keys (e.g. `"search.n_sigma"`). Previously nested
  changes were silently invisible.
- `update()` now accepts nested confid keys: pass a `dict` to update fields
  within a sub-config, or a `Config` instance to replace it. Previously
  passing a nested confid raised `KeyError`.
- `freeze()` now propagates to all nested sub-configs. Previously `freeze()`
  only blocked writes on flat fields of the top-level config.
- `freeze()` now also prevents replacing a nested sub-config via attribute
  assignment (e.g. `cfg.search = other`).
- CLI: `--field none` for `Seed` (and any field whose `from_string` returns
  `None`) now correctly applies `None` as the field value. Previously the
  `None` return from `from_string` was mistaken for "flag not supplied" and
  silently ignored.
- Nested `components=` are now stored in declaration order. Previously the
  internal dict had components in reverse order, causing sub-configs to appear
  in reversed order in `print(cfg)` and iteration.

# cfx 0.3.0 (2026-04-18)

## Features

- Added `transient` keyword to all field types. Callable defaults are now skipped
  during serialization when no explicit value has been stored — the callable
  reconstructs the value naturally on deserialization. Set `transient=False` to
  preserve the old snapshot behaviour instead.
- Config now implements `__iter__`, completing the dict-like protocol. `for key in cfg` works the same as `for key in cfg.keys()`.

## Bug Fixes

- Unroll composition (`method="unroll"`) now raises `ValueError` at class-definition time when two components share a field name. Previously the conflict was silently resolved by ordering. Override a component field by redeclaring it directly on the composing class.

## Removals

- Removed the `UserWarning` that fired when serializing a config with callable defaults. The warning fired even for correct usage and gave no actionable guidance. The correct behaviour (skip transient fields; use `transient=False` for snapshots) is now the default — see the `transient` feature entry.

## Documentation

- Composition docs updated: unroll field resolution order is now documented explicitly (inherited → components left-to-right → own fields), parallel name conflicts across components are called out with an error example, and the "first component wins" wording that described the old silent-override behaviour has been removed.

## Internal

- Migrated CI linting from flake8 to ruff. Added pre-commit hook running ruff format and ruff check.


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
