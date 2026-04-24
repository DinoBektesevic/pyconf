Serialization
=============

Configs can be persisted to a dict or YAML.  Choose based on context:

- **dict** - programmatic use, in-process transfer
- **YAML** - human-readable files, easy to hand-edit


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


.. note::

   Callable-default fields are **skipped** during serialization when no
   explicit value has been stored.  On load, the callable is still present in
   the class definition and reconstructs the value naturally.  See
   :ref:`sharp-edges-serialization` for details and edge cases.
