Fields
======

.. contents:: On this page
   :local:
   :depth: 2


Field types
-----------

All field types inherit from :class:`~cfx.ConfigField` and accept a
default value as their first argument and a ``doc`` string as their second.
Most also accept constraint parameters (``minval``, ``maxsize``, etc.) and a
``static=True`` flag (see `Static fields`_ below).

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Type
     - Description
   * - :class:`~cfx.ConfigField`
     - Base class.  No validation; accepts any value.  Use when you intend
       to subclass it (see `Defining your own field`_).
   * - :class:`~cfx.Any`
     - Explicit escape hatch.  No validation; signals to readers that the
       absence of constraints is intentional.
   * - :class:`~cfx.Bool`
     - ``True`` or ``False``.  Rejects ``int`` — unlike Python's own
       truthiness, ``1`` is not a ``bool`` here.
   * - :class:`~cfx.Int`
     - Integer.  Optional ``minval`` and ``maxval``.
   * - :class:`~cfx.Float`
     - Float.  Also accepts ``int`` on assignment.  Optional ``minval``
       and ``maxval``.
   * - :class:`~cfx.Scalar`
     - Either ``int`` or ``float``.  Use when both are acceptable.
       Optional ``minval`` and ``maxval``.
   * - :class:`~cfx.String`
     - Text string.  Optional ``minsize``, ``maxsize``, and ``predicate``
       (a callable that returns ``True`` for valid values).
   * - :class:`~cfx.Options`
     - One value from a fixed set.  Default is the first option unless
       ``default_value`` is supplied.
   * - :class:`~cfx.MultiOptions`
     - A ``set`` that is a subset of a fixed set of choices.
   * - :class:`~cfx.Path`
     - A ``pathlib.Path``.  Coerces plain strings on assignment.  Optional
       ``must_exist=True`` to reject paths that do not exist on disk.
   * - :class:`~cfx.Seed`
     - An ``int`` or ``None``.  ``None`` conventionally means "draw
       randomly at runtime".  Semantically distinct from ``Int(None, ...)``.
   * - :class:`~cfx.Range`
     - A ``(min, max)`` tuple.  Validates ``min < max``.  Linear ranges
       only — see `Defining your own field`_ for angular or cyclical ranges.
   * - :class:`~cfx.List`
     - A list.  Optional ``element_type``, ``minlen``, and ``maxlen``.
   * - :class:`~cfx.Dict`
     - An untyped dict.  Useful for free-form sub-structure that is too
       loose to warrant a nested :class:`~cfx.Config`.
   * - :class:`~cfx.Date`
     - A ``datetime.date``.
   * - :class:`~cfx.Time`
     - A ``datetime.time``.
   * - :class:`~cfx.DateTime`
     - A ``datetime.datetime``.  Rejects bare ``date`` instances.


Static fields
-------------

Set ``static=True`` to make a field's value a class-level constant.  Static
fields are readable on instances but raise ``AttributeError`` on any attempt
to set them::

    class RunConfig(Config):
        schema_rev = Int(2, "Config schema revision", static=True)
        timeout = Float(30.0, "Request timeout in seconds")

    cfg = RunConfig()
    cfg.schema_rev        # 2
    cfg.schema_rev = 3    # AttributeError: Cannot set a static config field.

Static values are shared across all instances and subclasses that do not
re-declare the field.  ``from_dict()`` ignores any serialized value for a
static field — the class-level default always wins.

To make a whole *instance* read-only after construction (rather than
individual fields), use :ref:`freeze` instead.


Cross-field validation
----------------------

Override :meth:`~cfx.Config.validate` to enforce constraints that span
multiple fields.  The base implementation does nothing.  It is called
automatically after every deserialization::

    class BandConfig(Config):
        low = Float(1.0, "Lower frequency bound", minval=0.0)
        high = Float(2.0, "Upper frequency bound", minval=0.0)

        def validate(self):
            if self.high <= self.low:
                raise ValueError(
                    f"high ({self.high}) must be greater than low ({self.low})"
                )

    BandConfig.from_dict({"low": 5.0, "high": 1.0})
    # ValueError: high (1.0) must be greater than low (5.0)

Call ``validate()`` manually at any time to recheck after interactive edits::

    cfg = BandConfig()
    cfg.low = 5.0
    cfg.validate()     # raises ValueError


.. _custom-fields:

Defining your own field
-----------------------

Subclass :class:`~cfx.ConfigField` and override :meth:`validate` to add
type or constraint checks.  Override :meth:`__set__` when you also need to
**transform** the value before storing it.

:class:`~cfx.Range` only supports linear ``(min, max)`` pairs — it cannot
represent an angular range like 350° to 10°, because "close" is
domain-specific.  A custom field handles this naturally::

    from cfx import Config, ConfigField, Float

    class Angle(ConfigField):
        """An angle in degrees, stored normalized to [0, 360)."""

        def validate(self, value):
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"Angle requires a number, got {type(value).__name__!r}"
                )

        def __set__(self, obj, value):
            if self.static:
                raise AttributeError("Cannot set a static config field.")
            self.validate(value)
            setattr(obj, self.private_name, float(value) % 360.0)


    class SurveyConfig(Config):
        heading = Angle(0.0, "Survey heading in degrees")
        bearing = Angle(45.0, "Bearing to target in degrees")
        radius = Float(10.0, "Search radius in meters", minval=0.0)

    cfg = SurveyConfig()
    cfg.heading = 370.0
    cfg.heading             # 10.0  — normalized to [0, 360)
    cfg.heading = -30.0
    cfg.heading             # 330.0 — wrapped around

    print(cfg)

.. code-block:: text

    SurveyConfig:
    Key     | Value | Description
    --------+-------+-------------------------------
    heading | 330.0 | Survey heading in degrees
    bearing | 45.0  | Bearing to target in degrees
    radius  | 10.0  | Search radius in meters

Any field type also accepts a **callable** as its default value.  The callable
receives the live config instance and is evaluated on every read where no
explicit value has been stored::

    class RetryConfig(Config):
        base_interval = Float(1.0, "Base interval in seconds", minval=0.0)
        retry_interval = Float(
            lambda self: self.base_interval * 3,
            "Retry interval; defaults to 3× base until overridden"
        )

    cfg = RetryConfig()
    cfg.retry_interval           # 3.0 — computed from base_interval

    cfg.base_interval = 2.0
    cfg.retry_interval           # 6.0 — recomputed

    cfg.retry_interval = 99.0    # store an explicit value
    cfg.retry_interval           # 99.0 — stored value; formula no longer called

See :doc:`advanced` for how to normalize a custom field's ``defaultval`` in
its ``__init__``, and for the full interaction between ``validate`` and
``__set__``.  See :ref:`sharp-edges-copy` and :ref:`sharp-edges-serialization`
for important caveats about copying and serializing configs with callable
defaults.
