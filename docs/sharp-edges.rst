Sharp edges
===========

This page documents subtle behaviors you may encounter with advanced
features.  Most users won't hit these, but they're important to understand
when using callable defaults or CLI string parsing.


.. _sharp-edges:


.. _sharp-edges-copy:

Callable fields and copy()
--------------------------

:meth:`~cfx.Config.copy` distinguishes between fields that have an
explicitly stored value and fields whose value comes from a callable default.
Only the stored values are copied - callable-default fields are left unset on
the new instance so they recompute lazily from the copy's own field values::

    class RetryConfig(Config):
        base = Float(1.0, "Base interval")
        retry = Float(lambda self: self.base * 3, "3* base")

    cfg = RetryConfig()   # retry NOT stored (callable default)
    cfg2 = cfg.copy()
    cfg2.base = 10.0
    cfg2.retry            # 30.0 - recomputed from cfg2.base

Once a callable-default field is explicitly set, ``copy()`` carries that
stored value::

    cfg.retry = 99.0      # now stored
    cfg3 = cfg.copy()
    cfg3.base = 10.0
    cfg3.retry            # 99.0 - the stored value is preserved, formula gone


.. _sharp-edges-serialization:

Serialization and callable defaults
------------------------------------

Callable-default fields are **skipped** during serialization when no explicit
value has been stored.  On load, the callable is still present in the class
definition and reconstructs the value naturally::

    class RetryConfig(Config):
        base = Float(1.0, "Base interval")
        retry = Float(lambda self: self.base * 3, "3* base")

    cfg = RetryConfig()
    d = cfg.to_dict()     # d == {'base': 1.0}  -- retry omitted

    cfg2 = RetryConfig.from_dict(d)
    cfg2.base = 10.0
    cfg2.retry            # 30.0 - recomputed from callable

This works reliably when the callable is a **pure function of other Config
fields**.  If the callable depends on external state (global variables,
memoized values, I/O), the reconstructed value after loading may differ from
the original.  In that case set ``transient=False`` on the field to preserve
the snapshot behavior::

    retry = Float(lambda self: self.base * 3, "3* base", transient=False)
    # now serialized as a plain value and reloaded as-is


Circular dependencies
---------------------

There is no cycle detection.  If field A's callable default reads field B
and field B's callable reads field A, you get infinite recursion::

    class BadConfig(Config):
        a = Float(lambda self: self.b + 1, "Reads b")
        b = Float(lambda self: self.a + 1, "Reads a")  # RecursionError on access

Keep the dependency graph acyclic: derived fields should only read
earlier-declared fields that have plain defaults.


``List.from_string`` falls back silently on bad JSON
-----------------------------------------------------

When a ``List`` field reads its value from an environment variable or a
CLI argument, it first tries to parse the raw string as JSON.  If that
fails (e.g. a malformed array), it silently falls back to splitting on
commas - so ``"[1, 2, 3"`` becomes ``["[1", " 2", " 3"]`` rather than an
error.

If precise element types matter, set ``element_type`` on the field and
pass well-formed JSON arrays from the environment.


.. _sharp-edges-normalization:

Normalization and the descriptor's defaultval
---------------------------------------------

``ConfigField.__init__`` runs the default through ``normalize()`` before
storing it, so ``defaultval`` is always in canonical form.  Instances and
the descriptor's ``defaultval`` agree::

    class SurveyConfig(Config):
        heading = Angle(370.0, "Heading in degrees")

    SurveyConfig().heading                       # 10.0 — normalized
    type(SurveyConfig()).heading.defaultval      # 10.0 — also normalized

This relies on ``normalize`` being idempotent.  If your ``normalize``
depends on instance state (rare), the class-level default may not match
what an instance would compute — keep ``normalize`` a pure function of
``value`` to avoid surprises.
