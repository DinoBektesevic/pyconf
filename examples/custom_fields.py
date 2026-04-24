"""Custom ConfigField subclasses: normalize → validate pipeline.

Shows three patterns:

1. Angle      — normalize wraps degrees to [0, 360); validate checks type.
2. LogScale   — validate enforces a log-space range; extra __init__ args.
3. Percentage — normalize rounds to configurable precision; validate checks
   [0, 100].

Usage:
    python custom_fields.py
"""

import math

from cfx import Config
from cfx.types import ConfigField

#############################################################################
# Custom field types
#############################################################################


class Angle(ConfigField):
    """Angle in degrees, automatically wrapped to [0, 360).

    Any numeric input is accepted; strings that can't be coerced raise in
    normalize() before validate() is ever called.
    """

    def normalize(self, value):
        return float(value) % 360.0

    def validate(self, value):
        if not isinstance(value, float):
            raise TypeError(
                f"Expected float after normalize, got {type(value).__name__!r}"
            )


class LogScale(ConfigField):
    """Value constrained to a log10-space range [10**log_min, 10**log_max].

    Extra constructor arguments must be set *before* calling super().__init__
    so that validate() (which is called on the default) can use them.
    """

    def __init__(self, default, doc, log_min, log_max, **kwargs):
        self.log_min = log_min
        self.log_max = log_max
        super().__init__(default, doc, **kwargs)

    def validate(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected number, got {type(value).__name__!r}")
        log_val = math.log10(value)
        if not (self.log_min <= log_val <= self.log_max):
            raise ValueError(
                f"log10({value}) = {log_val:.2f} is outside "
                f"[{self.log_min}, {self.log_max}]"
            )


class Percentage(ConfigField):
    """Percentage in [0.0, 100.0], optionally rounded to fixed precision."""

    def __init__(self, default, doc, precision=None, **kwargs):
        self.precision = precision
        super().__init__(default, doc, **kwargs)

    def normalize(self, value):
        result = float(value)
        if self.precision is not None:
            result = round(result, self.precision)
        return result

    def validate(self, value):
        if not (0.0 <= value <= 100.0):
            raise ValueError(f"Percentage {value} is outside [0, 100]")


#############################################################################
# Example usage
#############################################################################


class SurveyConfig(Config):
    confid = "survey"

    heading: float = Angle(0.0, "Survey heading (degrees)")
    sensitivity: float = LogScale(1.0, "Sensitivity", log_min=-2, log_max=2)
    confidence: float = Percentage(95.0, "Confidence level (%)", precision=1)


if __name__ == "__main__":
    cfg = SurveyConfig()

    cfg.heading = 370.0  # normalized to 10.0
    cfg.sensitivity = 0.1  # log10(0.1) = -1.0, in range
    cfg.confidence = 95.55  # rounded to 95.5 (precision=1, float repr)

    print(f"heading     = {cfg.heading}")  # 10.0
    print(f"sensitivity = {cfg.sensitivity}")  # 0.1
    print(f"confidence  = {cfg.confidence}")  # 95.5

    # Negative angles wrap correctly.
    cfg.heading = -90.0
    print(f"heading     = {cfg.heading}")  # 270.0

    # Out-of-range values raise immediately.
    try:
        cfg.sensitivity = 0.0001  # log10(0.0001) = -4, below log_min=-2
    except ValueError as e:
        print(f"ValueError: {e}")
