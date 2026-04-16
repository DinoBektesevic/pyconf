Sharp edges
===========

.. contents:: On this page
   :local:
   :depth: 1

.. _sharp-edges:


.. _sharp-edges-copy:

copy() and callable defaults
----------------------------

:meth:`~cfx.Config.copy` distinguishes between fields that have an
explicitly stored value and fields whose value comes from a callable default.
Only the stored values are copied — callable-default fields are left unset on
the new instance so they recompute lazily from the copy's own field values::

    class RetryConfig(Config):
        base = Float(1.0, "Base interval")
        retry = Float(lambda self: self.base * 3, "3× base")

    cfg = RetryConfig()   # retry NOT stored (callable default)
    cfg2 = cfg.copy()
    cfg2.base = 10.0
    cfg2.retry            # 30.0 — recomputed from cfg2.base ✓

Once a callable-default field is explicitly set, ``copy()`` carries that
stored value::

    cfg.retry = 99.0      # now stored
    cfg3 = cfg.copy()
    cfg3.base = 10.0
    cfg3.retry            # 99.0 — the stored value is preserved, formula gone


.. _sharp-edges-serialization:

Serialization and callable defaults
------------------------------------

``to_dict()`` serializes the *current computed value* of a callable-default
field, not the callable itself.  After a round-trip through
``from_dict()`` / ``from_yaml()`` / ``from_toml()``, the field holds a plain
stored value and will no longer recompute from its sibling.  A
``UserWarning`` is emitted when serializing a field that has never been
explicitly set::

    class RetryConfig(Config):
        base = Float(1.0, "Base interval")
        retry = Float(lambda self: self.base * 3, "3× base")

    cfg = RetryConfig()
    d = cfg.to_dict()     # UserWarning: 'retry' has a callable default…
                          # d == {'base': 1.0, 'retry': 3.0}

    cfg2 = RetryConfig.from_dict(d)
    cfg2.base = 10.0
    cfg2.retry            # 3.0 — baked in from dict, NOT recomputed ✗

**Workaround:** set all callable-default fields explicitly before serializing,
or accept that the formula is a live convenience rather than a persistent
relationship.


Circular dependencies
---------------------

There is no cycle detection.  If field A's callable default reads field B
and field B's callable reads field A, you get infinite recursion::

    class BadConfig(Config):
        a = Float(lambda self: self.b + 1, "Reads b")
        b = Float(lambda self: self.a + 1, "Reads a")  # RecursionError on access

Keep the dependency graph acyclic: derived fields should only read
earlier-declared fields that have plain defaults.


.. _sharp-edges-normalization:

Normalization and the descriptor's defaultval
---------------------------------------------

When a custom ``__set__`` normalizes values (as ``Angle`` does — see
:doc:`fields`), the transformation runs on every *instance* assignment
including the one ``Config.__init__`` makes when seeding the initial value.
The descriptor's own ``defaultval`` is validated but **not** transformed::

    class SurveyConfig(Config):
        heading = Angle(370.0, "Heading in degrees")

    SurveyConfig().heading                       # 10.0  — normalized ✓
    type(SurveyConfig()).heading.defaultval      # 370.0 — raw, not normalized

This is usually harmless because instances always see the normalized value.
If you need the descriptor's ``defaultval`` to be normalized too (e.g. for
introspection or equality checks), normalize it in ``Angle.__init__``.
See :doc:`advanced` for the full pattern.
