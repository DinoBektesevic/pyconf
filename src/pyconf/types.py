"""Typed configuration field descriptors.

Each class in this module implements a `ConfigField` specializations and their
validators; for practical reasons.
"""

import datetime
import numbers
import pathlib

from .config_field import ConfigField


__all__ = [
    "Any",
    "String",
    "Int",
    "Float",
    "Scalar",
    "Bool",
    "Options",
    "MultiOptions",
    "Path",
    "Seed",
    "Range",
    "List",
    "Dict",
    "Date",
    "Time",
    "DateTime",
]


class Any(ConfigField):
    """A field that accepts any value without validation.

    Use this as an explicit escape hatch when validation is intentionally
    deferred to `Config.validate` or handled externally. The ``Any`` name
    signals intent: the author has consciously opted out of field-level
    constraints.

    Parameters
    ----------
    default_value : `object` or `callable`
        Default value or lazy factory.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.
    """


class Options(ConfigField):
    """A field whose value must be one of a fixed set of choices.

    Parameters
    ----------
    options : `tuple` or `list`
        Allowed values. The first element is used as the default unless
        ``default_value`` is provided.
    doc : `str`
        Documentation.
    default_value : `object`, optional
        Default value. Must be a member of ``options``. Defaults to
        ``options[0]``.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    ValueError
        If the value being set is not in ``options``.

    Examples
    --------
    >>> from pyconf import Config, Options
    >>> class BaseConfig(Config):
    ...     mode = Options(("fast", "balanced", "thorough"), "Processing mode")
    >>> cfg = BaseConfig()
    >>> cfg.mode
    'fast'
    >>> cfg.mode = "thorough"
    >>> cfg.mode = "turbo"
    Traceback (most recent call last):
        ...
    ValueError: Expected 'turbo' to be one of ('fast', 'balanced', 'thorough')
    """

    def __init__(self, options, doc, default_value=None, static=False):
        self.options = options
        defaultval = options[0] if default_value is None else default_value
        super().__init__(defaultval, doc, static)

    def validate(self, value):
        if value not in self.options:
            raise ValueError(f"Expected {value!r} to be one of {self.options}")


class MultiOptions(ConfigField):
    """A field whose value must be a subset of a fixed set of choices.

    Parameters
    ----------
    options : `tuple` or `list`
        Full set of allowed values.
    doc : `str`
        Documentation.
    default_value : `set` or `frozenset`, optional
        Default selection. Defaults to an empty set.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `set` or `frozenset`.
    ValueError
        If the value contains elements not in ``options``.

    Examples
    --------
    >>> from pyconf import Config, MultiOptions
    >>> class PipelineConfig(Config):
    ...     steps = MultiOptions(
    ...         ("preprocess", "detect", "cluster", "output"),
    ...         "Pipeline steps to run",
    ...         default_value={"preprocess", "detect"},
    ...     )
    """

    def __init__(self, options, doc, default_value=None, static=False):
        self.options = set(options)
        defaultval = set() if default_value is None else default_value
        super().__init__(defaultval, doc, static)

    def __set__(self, obj, value):
        # Coerce list to set so that a round-trip through YAML/TOML (which
        # deserializes sequences as lists) does not fail validation.
        if isinstance(value, list):
            value = set(value)
        super().__set__(obj, value)

    def validate(self, value):
        if not isinstance(value, (set, frozenset)):
            raise TypeError(f"Expected a set, got {type(value).__name__!r}")
        extras = set(value) - self.options
        if extras:
            raise ValueError(
                f"Values {extras!r} are not in the allowed set {self.options!r}"
            )


class String(ConfigField):
    """A field that validates string values.

    Parameters
    ----------
    default_value : `str` or `callable`
        Default string value or lazy factory returning a `str`.
    doc : `str`
        Documentation.
    minsize : `int`, optional
        Minimum allowed string length. Default is ``0``.
    maxsize : `int` or `None`, optional
        Maximum allowed string length. `None` means no upper limit.
        Default is `None`.
    predicate : `callable` or `None`, optional
        Additional validation callable that accepts a `str` and returns
        `True` if the value is valid. Default is `None`.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `str`.
    ValueError
        If the value does not satisfy the length or predicate constraints.
    """

    def __init__(
        self,
        default_value,
        doc,
        minsize=0,
        maxsize=None,
        predicate=None,
        static=False
    ):
        self.minsize = minsize
        self.maxsize = maxsize
        self.predicate = predicate
        super().__init__(default_value, doc, static)

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError(f"Expected a str, got {type(value).__name__!r}")
        if len(value) < self.minsize:
            raise ValueError(
                f"Expected string of at least {self.minsize} characters, "
                f"got {len(value)}"
            )
        if self.maxsize is not None and len(value) > self.maxsize:
            raise ValueError(
                f"Expected string of at most {self.maxsize} characters, "
                f"got {len(value)}"
            )
        if self.predicate is not None and not self.predicate(value):
            raise ValueError(f"Value {value!r} failed predicate {self.predicate!r}")


class Scalar(ConfigField):
    """A field that validates numeric (int or float) values.

    Use this when both integers and floats are acceptable. For fields that
    must be strictly one numeric type, prefer `Int` or `Float`.

    Parameters
    ----------
    default_value : `numbers.Number` or `callable`
        Default numeric value or lazy factory returning a number.
    doc : `str`
        Documentation.
    minval : `numbers.Number` or `None`, optional
        Minimum allowed value (inclusive). Default is `None`.
    maxval : `numbers.Number` or `None`, optional
        Maximum allowed value (inclusive). Default is `None`.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `numbers.Number`.
    ValueError
        If the value is outside [``minval``, ``maxval``].
    """

    def __init__(
            self,
            default_value,
            doc,
            minval=None,
            maxval=None,
            static=False
    ):
        self.minval = minval
        self.maxval = maxval
        super().__init__(default_value, doc, static)

    def validate(self, value):
        if not isinstance(value, numbers.Number):
            raise TypeError(f"Expected a numeric value, got {type(value).__name__!r}")
        if self.minval is not None and value < self.minval:
            raise ValueError(f"Expected value >= {self.minval!r}, got {value!r}")
        if self.maxval is not None and value > self.maxval:
            raise ValueError(f"Expected value <= {self.maxval!r}, got {value!r}")


class Int(ConfigField):
    """A field that validates integer values.

    Parameters
    ----------
    default_value : `int` or `callable`
        Default integer value or lazy factory returning an `int`.
    doc : `str`
        Documentation.
    minval : `int` or `None`, optional
        Minimum allowed value (inclusive). Default is `None`.
    maxval : `int` or `None`, optional
        Maximum allowed value (inclusive). Default is `None`.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not an `int`.
    ValueError
        If the value is outside [``minval``, ``maxval``].
    """

    def __init__(
            self,
            default_value,
            doc,
            minval=None,
            maxval=None,
            static=False
    ):
        self.minval = minval
        self.maxval = maxval
        super().__init__(default_value, doc, static)

    def validate(self, value):
        if not isinstance(value, int):
            raise TypeError(f"Expected an int, got {type(value).__name__!r}")
        if self.minval is not None and value < self.minval:
            raise ValueError(f"Expected value >= {self.minval!r}, got {value!r}")
        if self.maxval is not None and value > self.maxval:
            raise ValueError(f"Expected value <= {self.maxval!r}, got {value!r}")


class Float(ConfigField):
    """A field that validates floating-point values.

    Parameters
    ----------
    default_value : `float` or `callable`
        Default float value or lazy factory returning a `float`.
    doc : `str`
        Documentation.
    minval : `float` or `None`, optional
        Minimum allowed value (inclusive). Default is `None`.
    maxval : `float` or `None`, optional
        Maximum allowed value (inclusive). Default is `None`.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `float` or `int` (ints are coerced).
    ValueError
        If the value is outside [``minval``, ``maxval``].
    """

    def __init__(
            self,
            default_value,
            doc,
            minval=None,
            maxval=None,
            static=False
    ):
        self.minval = minval
        self.maxval = maxval
        super().__init__(default_value, doc, static)

    def validate(self, value):
        if not isinstance(value, (float, int)):
            raise TypeError(f"Expected a float, got {type(value).__name__!r}")
        if self.minval is not None and value < self.minval:
            raise ValueError(f"Expected value >= {self.minval!r}, got {value!r}")
        if self.maxval is not None and value > self.maxval:
            raise ValueError(f"Expected value <= {self.maxval!r}, got {value!r}")


class Bool(ConfigField):
    """A field that validates boolean values.

    Parameters
    ----------
    default_value : `bool` or `callable`
        Default boolean value or lazy factory returning a `bool`.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `bool`.
    """

    def validate(self, value):
        if not isinstance(value, bool):
            raise TypeError(f"Expected a bool, got {type(value).__name__!r}")


class Path(ConfigField):
    """A field that coerces and validates filesystem paths.

    Accepts `str` or `pathlib.Path` values and stores them as
    `pathlib.Path` objects.

    Parameters
    ----------
    default_value : `str`, `pathlib.Path`, or `callable`
        Default path value or lazy factory. Strings are coerced to
        `pathlib.Path` on assignment.
    doc : `str`
        Documentation.
    must_exist : `bool`, optional
        If `True`, raises `ValueError` when the path does not exist on
        the filesystem at the time of assignment. Default is `False`.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value cannot be coerced to a `pathlib.Path`.
    ValueError
        If ``must_exist`` is `True` and the path does not exist.
    """

    def __init__(
            self,
            default_value,
            doc,
            must_exist=False,
            static=False
    ):
        self.must_exist = must_exist
        super().__init__(default_value, doc, static)

    def __set__(self, obj, value):
        # Re-check static here because we bypass super().__set__ (which carries
        # the static guard) in order to coerce the value before storing.
        if self.static:
            raise AttributeError("Cannot set a static config field.")
        try:
            value = pathlib.Path(value)
        except TypeError:
            raise TypeError(f"Expected a path-like value, got {type(value).__name__!r}")
        self.validate(value)
        setattr(obj, self.private_name, value)

    def validate(self, value):
        if not isinstance(value, pathlib.Path):
            return
        if self.must_exist and not value.exists():
            raise ValueError(f"Path does not exist: {value!r}")


class Seed(ConfigField):
    """A field for random-number-generator seeds.

    Accepts an `int` or `None`. A value of `None` signals that the seed
    should be chosen randomly at runtime, distinct from any specific integer
    seed including zero.

    Parameters
    ----------
    default_value : `int`, `None`, or `callable`
        Default seed value or lazy factory.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not an `int` or `None`.
    """

    def validate(self, value):
        if value is not None and not isinstance(value, int):
            raise TypeError(
                f"Expected an int or None for a seed value, "
                f"got {type(value).__name__!r}"
            )


class Range(ConfigField):
    """A field for a linear (min, max) numeric range.

    Stores a two-element tuple ``(min, max)`` and validates that
    ``min < max``. This field is intentionally limited to linear ranges.
    Cyclical or angular ranges (e.g. 350° to 10° crossing zero) are out
    of scope because their validation depends on domain-specific conventions.

    Parameters
    ----------
    default_value : `tuple` of two `numbers.Number`, or `callable`
        Default ``(min, max)`` tuple or lazy factory.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a two-element sequence of numbers.
    ValueError
        If ``min >= max``.
    """

    def __set__(self, obj, value):
        # Coerce list to tuple so that a round-trip through YAML/TOML (which
        # deserializes sequences as lists) does not change the stored type.
        if isinstance(value, list):
            value = tuple(value)
        super().__set__(obj, value)

    def validate(self, value):
        try:
            lo, hi = value
        except (TypeError, ValueError):
            raise TypeError(f"Expected a (min, max) pair, got {value!r}")
        if not (isinstance(lo, numbers.Number) and isinstance(hi, numbers.Number)):
            raise TypeError(f"Range bounds must be numeric, got {lo!r} and {hi!r}")
        if lo >= hi:
            raise ValueError(f"Expected min < max, got ({lo!r}, {hi!r})")


class List(ConfigField):
    """A field that validates list values.

    Parameters
    ----------
    default_value : `list` or `callable`
        Default list value or lazy factory returning a `list`.
    doc : `str`
        Documentation.
    element_type : `type` or `None`, optional
        If provided, every element of the list must be an instance of
        this type. Default is `None` (no element-level type check).
    minlen : `int` or `None`, optional
        Minimum number of elements. Default is `None`.
    maxlen : `int` or `None`, optional
        Maximum number of elements. Default is `None`.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `list`, or contains elements of the wrong
        type when ``element_type`` is set.
    ValueError
        If the list length is outside [``minlen``, ``maxlen``].
    """

    def __init__(
        self,
        default_value,
        doc,
        element_type=None,
        minlen=None,
        maxlen=None,
        static=False,
    ):
        self.element_type = element_type
        self.minlen = minlen
        self.maxlen = maxlen
        super().__init__(default_value, doc, static)

    def validate(self, value):
        if not isinstance(value, list):
            raise TypeError(f"Expected a list, got {type(value).__name__!r}")
        if self.minlen is not None and len(value) < self.minlen:
            raise ValueError(
                f"Expected list of at least {self.minlen} elements, got {len(value)}"
            )
        if self.maxlen is not None and len(value) > self.maxlen:
            raise ValueError(
                f"Expected list of at most {self.maxlen} elements, got {len(value)}"
            )
        if self.element_type is not None:
            bad = [el for el in value if not isinstance(el, self.element_type)]
            if bad:
                raise TypeError(
                    f"All elements must be {self.element_type.__name__!r}, "
                    f"found {bad!r}"
                )


class Dict(ConfigField):
    """A field that validates dict values.

    Accepts any `dict`. Use this for free-form sub-structure that is too
    loosely typed to warrant a nested `Config`, but too structured to be
    a `String`.

    Parameters
    ----------
    default_value : `dict` or `callable`
        Default dict value or lazy factory returning a `dict`.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `dict`.
    """

    def validate(self, value):
        if not isinstance(value, dict):
            raise TypeError(f"Expected a dict, got {type(value).__name__!r}")


class Date(ConfigField):
    """A field that validates `datetime.date` values.

    Parameters
    ----------
    default_value : `datetime.date` or `callable`
        Default date value or lazy factory returning a `datetime.date`.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `datetime.date`.
    """

    def validate(self, value):
        if not isinstance(value, datetime.date):
            raise TypeError(f"Expected a datetime.date, got {type(value).__name__!r}")


class Time(ConfigField):
    """A field that validates `datetime.time` values.

    Parameters
    ----------
    default_value : `datetime.time` or `callable`
        Default time value or lazy factory returning a `datetime.time`.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `datetime.time`.
    """

    def __set__(self, obj, value):
        # Coerce ISO-format string to datetime.time so that round-trips through
        # to_dict/from_dict work: datetime.time has no native YAML safe
        # representation, so _serialize_value emits an ISO string instead.
        if isinstance(value, str):
            value = datetime.time.fromisoformat(value)
        super().__set__(obj, value)

    def validate(self, value):
        if not isinstance(value, datetime.time):
            raise TypeError(f"Expected a datetime.time, got {type(value).__name__!r}")


class DateTime(ConfigField):
    """A field that validates `datetime.datetime` values.

    Parameters
    ----------
    default_value : `datetime.datetime` or `callable`
        Default datetime value or lazy factory returning a
        `datetime.datetime`.
    doc : `str`
        Documentation.
    static : `bool`, optional
        If `True`, the value is frozen at class-definition time.
        Default is `False`.

    Raises
    ------
    TypeError
        If the value is not a `datetime.datetime`.
    """

    def validate(self, value):
        if not isinstance(value, datetime.datetime):
            raise TypeError(
                f"Expected a datetime.datetime, got {type(value).__name__!r}"
            )
