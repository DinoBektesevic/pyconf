Using configs
=============

.. contents:: On this page
   :local:
   :depth: 1


Accessing and setting fields
----------------------------

::

    cfg = ProcessingConfig()

    cfg.iterations   # 100 — dot access
    cfg["mode"]      # 'fast' — dict-style access

    cfg.iterations = 200       # dot assignment
    cfg["mode"] = "thorough"   # dict-style assignment

    list(cfg.keys())   # ['iterations', 'threshold', 'label', 'mode', 'verbose']
    cfg.values()       # [200, 0.5, 'run_01', 'thorough', False]
    dict(cfg.items())  # {'iterations': 200, ..., 'mode': 'thorough', ...}


Comparison
----------

Two config instances compare equal when all their field values are equal::

    cfg1 = ProcessingConfig()
    cfg2 = ProcessingConfig()
    cfg1 == cfg2   # True

    cfg1.mode = "thorough"
    cfg1 == cfg2   # False


Copying and diffing
-------------------

:meth:`~pyconf.Config.copy` returns a new instance with the same field values.
Pass keyword arguments to override specific fields in the copy::

    base = ProcessingConfig()
    modified = base.copy(iterations=500, mode="thorough")

:meth:`~pyconf.Config.diff` returns a dict of the fields that differ between
two instances of the same type::

    base.diff(modified)
    # {'iterations': (100, 500), 'mode': ('fast', 'thorough')}

See :ref:`sharp-edges-copy` for important behaviour to know about when the
config has callable (computed) defaults.


Updating
--------

:meth:`~pyconf.Config.update` applies several field changes at once.  Each
value goes through the same descriptor validation as direct assignment::

    cfg.update({"iterations": 50, "threshold": 0.8})


.. _freeze:

Freezing
--------

:meth:`~pyconf.Config.freeze` makes an instance read-only.  Any subsequent
field assignment raises :exc:`~pyconf.FrozenConfigError`::

    cfg = ProcessingConfig()
    cfg.freeze()
    cfg.iterations = 10    # FrozenConfigError: Cannot set field 'iterations' ...

Freezing is instance-level — other instances of the same class are unaffected.
To freeze individual fields at the class level instead of entire instances,
use ``static=True`` on the field declaration (see :doc:`fields`).


Saving and loading
------------------

::

    d = cfg.to_dict()
    cfg2 = ProcessingConfig.from_dict(d)

For YAML, TOML, and round-trip details see :doc:`serialization`.
