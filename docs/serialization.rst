Serialization
=============

.. contents:: On this page
   :local:
   :depth: 1


dict
----

:meth:`~cfx.Config.to_dict` / :meth:`~cfx.Config.from_dict` convert
to and from a plain Python dict.  ``from_dict`` calls
:meth:`~cfx.Config.validate` automatically after loading::

    d    = cfg.to_dict()
    cfg2 = ProcessingConfig.from_dict(d)

Pass ``strict=False`` to silently ignore unknown keys — useful when loading
config files written by an older version of your code::

    cfg3 = ProcessingConfig.from_dict(saved_dict, strict=False)

By default (``strict=True``) an unknown key raises ``KeyError``.


YAML
----

YAML round-trips require ``pyyaml``::

    yaml_str = cfg.to_yaml()                          # pip install pyyaml
    cfg4     = ProcessingConfig.from_yaml(yaml_str)


TOML
----

TOML round-trips require ``tomli-w`` to write and ``tomllib`` (stdlib,
Python ≥ 3.11) or ``tomli`` to read::

    toml_str = cfg.to_toml()                           # pip install tomli-w
    cfg5     = ProcessingConfig.from_toml(toml_str)    # tomllib or tomli

.. note::

   Fields with callable defaults serialize as a **snapshot** of the current
   computed value.  After a round-trip the field holds a plain stored value
   and will no longer recompute from its sibling.  A ``UserWarning`` is
   emitted when this happens.  See :ref:`sharp-edges-serialization` for
   details and a workaround.
