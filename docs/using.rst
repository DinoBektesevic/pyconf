Using configs
=============

This page covers runtime operations on config instances: reading and
modifying fields, comparing and copying instances, making them read-only,
and saving or loading values.


Accessing and setting fields
----------------------------

::

    cfg = ProcessingConfig()

    cfg.iterations   # 100 - dot access
    cfg["mode"]      # 'fast' - dict-style access

    cfg.iterations = 200       # dot assignment
    cfg["mode"] = "thorough"   # dict-style assignment

    list(cfg.keys())   # ['iterations', 'threshold', 'label', 'mode', 'verbose']
    cfg.values()       # [200, 0.5, 'run_01', 'thorough', False]
    dict(cfg.items())  # {'iterations': 200, ..., 'mode': 'thorough', ...}


Updating
--------

:meth:`~cfx.Config.update` applies several field changes at once.  Each
value goes through the same descriptor validation as direct assignment, and
:meth:`~cfx.Config.validate` is called at the end to enforce cross-field
invariants::

    cfg.update({"iterations": 50, "threshold": 0.8})


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

:meth:`~cfx.Config.copy` returns a new instance with the same field values.
Pass keyword arguments to override specific fields in the copy::

    base = ProcessingConfig()
    modified = base.copy(iterations=500, mode="thorough")

:meth:`~cfx.Config.diff` returns a dict of the fields that differ between
two instances of the same type::

    base.diff(modified)
    # {'iterations': (100, 500), 'mode': ('fast', 'thorough')}

See :ref:`sharp-edges-copy` for important behaviour to know about when the
config has callable (computed) defaults.


.. _freeze:

Freezing
--------

:meth:`~cfx.Config.freeze` makes an instance read-only.  Any subsequent
field assignment raises :exc:`~cfx.FrozenConfigError`::

    cfg = ProcessingConfig()
    cfg.freeze()
    cfg.iterations = 10    # FrozenConfigError: Cannot set field 'iterations' ...

Freezing is instance-level - other instances of the same class are unaffected.
To freeze individual fields at the class level instead of entire instances,
use ``static=True`` on the field declaration (see :doc:`fields`).


Checking and resetting field state
-----------------------------------

:meth:`~cfx.ConfigField.is_set`, :meth:`~cfx.ConfigField.unset`, and
:meth:`~cfx.ConfigField.reset` are methods on the field descriptor.  They
take a config instance as their first argument::

    class Derived(Config):
        base: float = Field(1.0, "Base value")
        triple: float = Field(lambda self: self.base * 3, "3× base")

    cfg = Derived()

    f_base   = Derived._fields["base"]
    f_triple = Derived._fields["triple"]

    f_base.is_set(cfg)    # True  — seeded from default by __init__
    f_triple.is_set(cfg)  # False — callable default, not pre-populated

    cfg.base = 10.0
    f_base.is_set(cfg)    # True
    cfg.triple            # 30.0  — computed on access

    cfg.triple = 99.0
    f_triple.is_set(cfg)  # True  — now explicitly stored

    f_triple.unset(cfg)
    f_triple.is_set(cfg)  # False — reverts to callable default
    cfg.triple            # 30.0  — computed again

    f_triple.reset(cfg, 5.0)    # same as cfg.triple = 5.0
    f_triple.reset(cfg)         # same as unset()


Saving and loading
------------------

::

    d = cfg.to_dict()
    cfg2 = ProcessingConfig.from_dict(d)

For YAML and round-trip details see :doc:`serialization`.
