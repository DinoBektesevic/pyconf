Custom Fields
=============

When the built-in types don't fit your domain — non-linear ranges, custom unit
normalization, domain-specific coercion — extend :class:`~cfx.ConfigField`
directly.  This capability is intentionally preserved alongside
annotation-native syntax: not every field can be expressed via annotations
alone.


Defining your own field
-----------------------

Import the base class from ``cfx.types``::

    from cfx import Config, Field
    from cfx.types import ConfigField

    class Angle(ConfigField):
        """An angle in degrees, stored normalized to [0, 360)."""

        def normalize(self, value):
            """Coerce to float and wrap to [0, 360)."""
            return float(value) % 360.0

        def validate(self, value):
            if not isinstance(value, float):
                raise TypeError(
                    f"Angle requires a float, got {type(value).__name__!r}"
                )


    class SurveyConfig(Config):
        heading = Angle(0.0, "Survey heading in degrees")
        bearing = Angle(45.0, "Bearing to target in degrees")
        radius: float = Field(10.0, "Search radius in meters", minval=0.0)

    cfg = SurveyConfig()
    cfg.heading = 370.0
    cfg.heading             # 10.0  - normalized to [0, 360)
    cfg.heading = -30.0
    cfg.heading             # 330.0 - wrapped around

Explicit field types and ``Field()``-declared fields can coexist freely on
the same class.


Normalize and validate
----------------------

Every assignment (and the initial seeding of the default value) runs through
the same two-step pipeline:

1. ``normalize(value)`` — transform the raw input to its canonical form.
   Must be idempotent: ``normalize(normalize(x)) == normalize(x)`` (see
   :ref:`sharp-edges-normalization` for when relaxing this is acceptable).
2. ``validate(value)`` — check the normalized value against constraints.
   Raise ``TypeError`` or ``ValueError`` on failure.

Both methods are called in ``ConfigField.__init__`` on the default, so
``defaultval`` is always stored in its canonical (normalized) form::

    class SurveyConfig(Config):
        heading = Angle(370.0, "Heading")

    SurveyConfig().heading                   # 10.0 — normalized at access
    type(SurveyConfig()).heading.defaultval  # 10.0 — also normalized

Override only the methods you need.  The base implementations are no-ops —
``normalize`` returns the value unchanged, ``validate`` accepts anything.


Extra constructor arguments
---------------------------

Custom ``__init__`` parameters must be set *before* calling
``super().__init__`` because the parent calls ``validate`` on the default::

    import math

    class LogScale(ConfigField):
        """Value constrained to a log10-space interval."""

        def __init__(self, default, doc, log_min, log_max, **kwargs):
            self.log_min = log_min
            self.log_max = log_max
            super().__init__(default, doc, **kwargs)

        def validate(self, value):
            log_val = math.log10(value)
            if not (self.log_min <= log_val <= self.log_max):
                raise ValueError(
                    f"log10({value}) = {log_val:.2f} outside "
                    f"[{self.log_min}, {self.log_max}]"
                )


Serialization hooks
-------------------

Override ``serialize`` and ``deserialize`` to control how a field value is
stored in a dict or YAML file.  By default both are identity functions.

The ``Path`` field, for example, converts to a plain string for serialization
and back to ``pathlib.Path`` on load::

    import pathlib

    class MyPath(ConfigField):
        def normalize(self, value):
            if isinstance(value, str):
                return pathlib.Path(value)
            return value

        def serialize(self, value):
            return str(value)

        def deserialize(self, value):
            return pathlib.Path(value)

``serialize`` is called by :meth:`~cfx.Config.to_dict` (and therefore
``to_yaml``).  ``deserialize`` is called by :meth:`~cfx.Config.from_dict`
before the value is passed through the normalize → validate pipeline.


CLI hooks
---------

Override ``to_argparse_kwargs`` (or ``to_click_option``) to control how a
field is exposed on the command line.  The base implementation returns a
``type=from_string`` callable and an appropriate metavar; override only what
differs from that default::

    class Angle(ConfigField):
        ...

        def to_argparse_kwargs(self, name, prefix=""):
            kwargs = super().to_argparse_kwargs(name, prefix)
            kwargs["metavar"] = "DEG"
            kwargs["help"] = f"{self.doc} (any value, wrapped to [0, 360))"
            return kwargs
