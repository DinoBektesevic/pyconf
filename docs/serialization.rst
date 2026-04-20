Serialization
=============

Configs can be persisted to a dict, YAML, or TOML.  Choose based on context:

- **dict** - programmatic use, in-process transfer
- **YAML** - human-readable files, easy to hand-edit
- **TOML** - structured config files with strong typing


dict
----

:meth:`~cfx.Config.to_dict` / :meth:`~cfx.Config.from_dict` convert
to and from a plain Python dict.  ``from_dict`` calls
:meth:`~cfx.Config.validate` automatically after loading::

    d    = cfg.to_dict()
    cfg2 = ProcessingConfig.from_dict(d)

Pass ``strict=False`` to silently ignore unknown keys - useful when loading
config files written by an older version of your code::

    cfg3 = ProcessingConfig.from_dict(saved_dict, strict=False)

By default (``strict=True``) an unknown key raises ``KeyError``.


YAML
----

YAML round-trips require ``pyyaml``::

    yaml_str = cfg.to_yaml()                          # pip install pyyaml
    cfg4     = ProcessingConfig.from_yaml(yaml_str)

For ``ProcessingConfig`` with default values the output looks like:

.. code-block:: yaml

    iterations: 100
    threshold: 0.5
    label: run_01
    mode: fast
    verbose: false

Nested configs produce a nested YAML structure keyed by ``confid``.


TOML
----

TOML round-trips require ``tomli-w`` to write and ``tomllib`` (stdlib,
Python >= 3.11) or ``tomli`` to read::

    toml_str = cfg.to_toml()                           # pip install tomli-w
    cfg5     = ProcessingConfig.from_toml(toml_str)    # tomllib or tomli

.. warning::

   ``to_toml()`` silently drops fields whose value is ``None``, because
   TOML has no null type.  ``to_dict()`` and ``to_yaml()`` preserve ``None``
   values.  If you need to round-trip ``None`` through TOML, use a sentinel
   value instead (e.g. ``-1`` for a seed or an empty string for optional
   text).

.. note::

   Callable-default fields are **skipped** during serialization when no
   explicit value has been stored.  On load, the callable is still present in
   the class definition and reconstructs the value naturally.  See
   :ref:`sharp-edges-serialization` for details and edge cases.
