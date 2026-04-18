Fields
======

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
     - ``True`` or ``False``.  Rejects ``int`` - unlike Python's own
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
       ``default_value`` is supplied.  **Note:** the constructor takes
       ``(options, doc, default_value=None, ...)`` - the allowed choices come
       first, unlike most other field types where the default value comes first.
   * - :class:`~cfx.MultiOptions`
     - A ``set`` that is a subset of a fixed set of choices.  Same
       constructor order as ``Options``: ``(options, doc, default_value=None, ...)``.
   * - :class:`~cfx.Path`
     - A ``pathlib.Path``.  Coerces plain strings on assignment.  Optional
       ``must_exist=True`` to reject paths that do not exist on disk.
   * - :class:`~cfx.Seed`
     - An ``int`` or ``None``.  ``None`` conventionally means "draw
       randomly at runtime".  Semantically distinct from ``Int(None, ...)``.
   * - :class:`~cfx.Range`
     - A ``(min, max)`` tuple.  Validates ``min < max``.  Linear ranges
       only - see `Defining your own field`_ for angular or cyclical ranges.
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
static field - the class-level default always wins.

To make a whole *instance* read-only after construction (rather than
individual fields), use :ref:`freeze` instead.


Environment variables
---------------------

Pass ``env=`` to any field to read its default from an environment variable
when no explicit value has been stored on the instance::

    import os
    from cfx import Config, String, Int

    class DatabaseConfig(Config):
        host = String("localhost", "Database host", env="DB_HOST")
        port = Int(5432, "Database port", env="DB_PORT")

    os.environ["DB_HOST"] = "db.example.com"
    cfg = DatabaseConfig()
    cfg.host    # 'db.example.com' - from env var
    cfg.port    # 5432 - env var not set; falls back to default

The lookup priority on every field read is:

1. An explicit value stored on the instance (via assignment or
   :meth:`~cfx.Config.from_dict`).
2. The environment variable named by ``env``, if the variable is present in
   ``os.environ``.
3. The ``default_value`` passed to the field constructor (called if callable).

Environment variable reads are **lazy**: the variable is looked up on every
read where no explicit value is stored, not snapshotted at construction.
This makes it straightforward to vary the environment between test cases::

    os.environ["DB_HOST"] = "primary.example.com"
    cfg = DatabaseConfig()
    cfg.host    # 'primary.example.com'

    os.environ["DB_HOST"] = "replica.example.com"
    cfg.host    # 'replica.example.com' - re-read each time

Once an explicit value is stored, the environment variable is no longer
consulted::

    cfg.host = "override.example.com"
    os.environ["DB_HOST"] = "ignored"
    cfg.host    # 'override.example.com'

The raw environment string is parsed with the field's
:meth:`~cfx.ConfigField.from_string` method, so typed fields (``Int``,
``Float``, ``Bool``, etc.) coerce and validate the value automatically.


Cross-field validation
----------------------

Configs contain :class:`~cfx.ConfigField` instances, each of which validates
only its own value, they cannot enforce relationships between fields.
Override :meth:`~cfx.Config.validate` on the config class to enforce
cross-field consistency.  By default the config-level validator performs no
checks.

``validate()`` is called automatically by :meth:`~cfx.Config.from_dict`,
:meth:`~cfx.Config.from_yaml`, and :meth:`~cfx.Config.from_toml` after
loading.  Individual field assignments do **not** trigger it.  You must ensure
cross-field consistency by manually invoking it at critical points in your
code::

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

When the built-in types don't fit your domain (non-linear ranges, custom
unit normalization, domain-specific enums), extending
:class:`~cfx.ConfigField` is straightforward.  Subclass it and override:

- :meth:`validate`: adds type or constraint checks
- :meth:`__set__`: applies transformations to the value before storing it
  (normalization, type coercion, wrapping, etc.)

:class:`~cfx.Range` only supports linear ``(min, max)`` pairs.  Angles wrap
around: 359° and 1° are only 2° apart, but a linear range has no way to
express that.  A custom field handles this naturally, normalizing any
assigned value into ``[0, 360)``::

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
    cfg.heading             # 10.0  - normalized to [0, 360)
    cfg.heading = -30.0
    cfg.heading             # 330.0 - wrapped around

    print(cfg)

.. code-block:: text

    SurveyConfig:
    Config       | Key     | Value | Description
    -------------+---------+-------+-------------------------------
    SurveyConfig | heading | 330.0 | Survey heading in degrees
    SurveyConfig | bearing | 45.0  | Bearing to target in degrees
    SurveyConfig | radius  | 10.0  | Search radius in meters

Computed fields
---------------

Any field type accepts a **callable** as its default value.  The callable
receives the live config instance and is evaluated on every read where no
explicit value has been stored.

A lambda works well for simple derived fields.  Here, multiple detection
thresholds scale automatically from a single measured standard deviation.
``sigma3`` is marked ``static=True``, i.e. by definition it is ``stddev * 3``
and cannot be overridden::

    class DetectionConfig(Config):
        stddev = Float(1.0, "Measured standard deviation")
        sigma3 = Float(lambda self: self.stddev * 3, "3-sigma threshold",
                       static=True)
        sigma5 = Float(lambda self: self.stddev * 5, "5-sigma threshold")
        sigma7 = Float(lambda self: self.stddev * 7, "7-sigma threshold")

    cfg = DetectionConfig()
    cfg.stddev = 2.0
    cfg.sigma3   # 6.0
    cfg.sigma5   # 10.0
    cfg.sigma7   # 14.0

    cfg.sigma5 = 99.0   # store an explicit override
    cfg.sigma5          # 99.0 - stored value; formula no longer called

    cfg.sigma3 = 99.0   # AttributeError: Cannot set a static config field.

A named function is better when the logic is non-trivial or you want to
reuse it across config classes.  Write the function with explicit arguments,
then use a lambda to wire it to the config's fields::

    def exponential_backoff(base_interval, attempt):
        return base_interval * (2 ** attempt)

    class RetryConfig(Config):
        base_interval = Float(1.0, "Base retry interval in seconds", minval=0.0)
        attempt = Int(0, "Current retry attempt", minval=0)
        interval = Float(
            lambda self: exponential_backoff(self.base_interval, self.attempt),
            "Retry interval for current attempt"
        )

    cfg = RetryConfig()
    cfg.interval    # 1.0 - attempt 0: 1.0 * 2^1

    cfg.attempt = 1
    cfg.interval    # 2.0 - attempt 1: 1.0 * 2^2

    cfg.attempt = 3
    cfg.interval    # 8.0 - attempt 3: 1.0 * 2^3

Because ``exponential_backoff`` is an ordinary function, it can be reused
in a different config without being rewritten::

    class AggressiveRetryConfig(Config):
        base_interval = Float(0.5, "Base retry interval in seconds", minval=0.0)
        attempt = Int(0, "Current retry attempt", minval=0)
        interval = Float(
            lambda self: exponential_backoff(self.base_interval, self.attempt),
            "Retry interval for current attempt"
        )

     exponential_backoff(0.5, 2)

Callable defaults are skipped during serialization when no explicit value has
been stored - they reconstruct from the class definition on load.  This works
as long as the callable is a pure function of other Config fields.  See
:ref:`sharp-edges-serialization` if your callable depends on external state.

See :doc:`advanced` for how to normalize a custom field's ``defaultval`` in
its ``__init__``, and for the full interaction between ``validate`` and
``__set__``.  See :ref:`sharp-edges-copy` for copy behavior with callable
defaults.
