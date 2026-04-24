"""Typed configuration field descriptors and view field types.

Each concrete class here is a `ConfigField` specialization.  `Alias` and
`Mirror` are descriptor classes declared on views or configs to wire fields
together.
"""

import datetime
import json
import numbers
import pathlib

from ..refs import FieldRef
from ..utils import walk, walk_set

try:
    import click as _click
except ImportError:
    _click = None

from .config_field import ConfigField

__all__ = [
    "ConfigField",
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
    "Alias",
    "Mirror",
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
    >>> from cfx import Config
    >>> from cfx.types import Options
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

    def __init__(
        self,
        options,
        doc,
        default_value=None,
        static=False,
        env=None,
        transient=None,
    ):
        self.options = options
        defaultval = options[0] if default_value is None else default_value
        super().__init__(
            defaultval,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def validate(self, value):  # noqa: D102
        if value not in self.options:
            raise ValueError(f"Expected {value!r} to be one of {self.options}")

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["choices"] = list(self.options)
        return kwargs

    def to_click_option(self, name, prefix=""):  # noqa: D102
        if _click is None:
            raise ImportError(
                "click is required for click_options(). "
                "Install it with: pip install click"
            )
        hyphenated = name.replace("_", "-")
        flag = f"--{prefix}.{hyphenated}" if prefix else f"--{hyphenated}"
        param_name = f"{prefix.replace('.', '__')}__{name}" if prefix else name
        return _click.option(
            flag,
            param_name,
            type=_click.Choice(list(self.options)),
            default=None,
            help=self.doc,
            show_default=False,
        )


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
    >>> from cfx import Config
    >>> from cfx.types import MultiOptions
    >>> class PipelineConfig(Config):
    ...     steps = MultiOptions(
    ...         ("preprocess", "detect", "cluster", "output"),
    ...         "Pipeline steps to run",
    ...         default_value={"preprocess", "detect"},
    ...     )
    """

    def __init__(
        self,
        options,
        doc,
        default_value=None,
        static=False,
        env=None,
        transient=None,
    ):
        self.options = set(options)
        defaultval = set() if default_value is None else default_value
        super().__init__(
            defaultval,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def normalize(self, value):  # noqa: D102
        # Coerce list/tuple -> set: YAML deserializes sequences as lists,
        # and click's multiple=True returns a tuple.
        if isinstance(value, (list, tuple)):
            return set(value)
        return value

    def validate(self, value):  # noqa: D102
        if not isinstance(value, (set, frozenset)):
            raise TypeError(f"Expected a set, got {type(value).__name__!r}")
        extras = set(value) - self.options
        if extras:
            raise ValueError(
                f"Expected {self.options!r}, got {extras!r} instead"
            )

    def serialize(self, value):  # noqa: D102
        return sorted(value, key=str)

    def deserialize(self, value):  # noqa: D102
        if isinstance(value, (list, tuple)):
            return set(value)
        return value

    def from_string(self, s):  # noqa: D102
        return {item.strip() for item in s.split(",") if item.strip()}

    def to_string(self, value):  # noqa: D102
        return "{" + ", ".join(sorted(str(x) for x in value)) + "}"

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["nargs"] = "+"
        kwargs["choices"] = list(self.options)
        kwargs["type"] = str
        return kwargs

    def to_click_option(self, name, prefix=""):  # noqa: D102
        if _click is None:
            raise ImportError(
                "click is required for click_options(). "
                "Install it with: pip install click"
            )
        hyphenated = name.replace("_", "-")
        flag = f"--{prefix}.{hyphenated}" if prefix else f"--{hyphenated}"
        param_name = f"{prefix.replace('.', '__')}__{name}" if prefix else name
        return _click.option(
            flag,
            param_name,
            type=_click.Choice(list(self.options)),
            multiple=True,
            default=None,
            help=self.doc,
            show_default=False,
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
        static=False,
        env=None,
        transient=None,
    ):
        self.minsize = minsize
        self.maxsize = maxsize
        self.predicate = predicate
        super().__init__(
            default_value,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def validate(self, value):  # noqa: D102
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
            raise ValueError(
                f"Value {value!r} failed predicate {self.predicate!r}"
            )


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
        static=False,
        env=None,
        transient=None,
    ):
        self.minval = minval
        self.maxval = maxval
        super().__init__(
            default_value,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def from_string(self, s):  # noqa: D102
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError as err:
            raise ValueError(
                f"Cannot parse {s!r} as a number (env var {self.env!r})"
            ) from err

    def validate(self, value):  # noqa: D102
        if not isinstance(value, numbers.Number):
            raise TypeError(
                f"Expected a numeric value, got {type(value).__name__!r}"
            )
        if self.minval is not None and value < self.minval:
            raise ValueError(
                f"Expected value >= {self.minval!r}, got {value!r}"
            )
        if self.maxval is not None and value > self.maxval:
            raise ValueError(
                f"Expected value <= {self.maxval!r}, got {value!r}"
            )


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
    env : `str` or `None`, optional
        Environment variable name. See `ConfigField`.

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
        static=False,
        env=None,
        transient=None,
    ):
        self.minval = minval
        self.maxval = maxval
        super().__init__(
            default_value,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def from_string(self, s):  # noqa: D102
        try:
            return int(s)
        except ValueError as err:
            raise ValueError(
                f"Cannot parse {s!r} as int (env var {self.env!r})"
            ) from err

    def validate(self, value):  # noqa: D102
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"Expected an int, got {type(value).__name__!r}")
        if self.minval is not None and value < self.minval:
            raise ValueError(
                f"Expected value >= {self.minval!r}, got {value!r}"
            )
        if self.maxval is not None and value > self.maxval:
            raise ValueError(
                f"Expected value <= {self.maxval!r}, got {value!r}"
            )


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
    env : `str` or `None`, optional
        Environment variable name. See `ConfigField`.

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
        static=False,
        env=None,
        transient=None,
    ):
        self.minval = minval
        self.maxval = maxval
        super().__init__(
            default_value,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def from_string(self, s):  # noqa: D102
        try:
            return float(s)
        except ValueError as err:
            raise ValueError(
                f"Cannot parse {s!r} as float (env var {self.env!r})"
            ) from err

    def validate(self, value):  # noqa: D102
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise TypeError(f"Expected a float, got {type(value).__name__!r}")
        if self.minval is not None and value < self.minval:
            raise ValueError(
                f"Expected value >= {self.minval!r}, got {value!r}"
            )
        if self.maxval is not None and value > self.maxval:
            raise ValueError(
                f"Expected value <= {self.maxval!r}, got {value!r}"
            )


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

    def from_string(self, s):  # noqa: D102
        if s.lower() in ("1", "true", "yes", "on"):
            return True
        if s.lower() in ("0", "false", "no", "off"):
            return False
        raise ValueError(
            f"Cannot parse {s!r} as bool (env var {self.env!r}). "
            f"Use 1/0, true/false, yes/no, or on/off."
        )

    def validate(self, value):  # noqa: D102
        if not isinstance(value, bool):
            raise TypeError(f"Expected a bool, got {type(value).__name__!r}")

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        import argparse

        kwargs = super().to_argparse_kwargs(name, prefix)
        del kwargs["type"]
        kwargs["action"] = argparse.BooleanOptionalAction
        return kwargs

    def to_click_option(self, name, prefix=""):  # noqa: D102
        if _click is None:
            raise ImportError(
                "click is required for click_options(). "
                "Install it with: pip install click"
            )
        hyphenated = name.replace("_", "-")
        if prefix:
            flag_pair = f"--{prefix}.{hyphenated}/--{prefix}.no-{hyphenated}"
            param_name = f"{prefix.replace('.', '__')}__{name}"
        else:
            flag_pair = f"--{hyphenated}/--no-{hyphenated}"
            param_name = name
        return _click.option(
            flag_pair,
            param_name,
            default=None,
            help=self.doc,
            show_default=False,
        )


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
        static=False,
        env=None,
        transient=None,
    ):
        self.must_exist = must_exist
        super().__init__(
            default_value,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def normalize(self, value):  # noqa: D102
        # Coerce str/os.PathLike -> pathlib.Path. Let validate() handle
        # any TypeError if the value is truly not path-like.
        try:
            return pathlib.Path(value)
        except TypeError:
            return value

    def validate(self, value):  # noqa: D102
        if not isinstance(value, pathlib.Path):
            raise TypeError(f"Expected a Path, got {type(value).__name__!r}")
        if self.must_exist and not value.exists():
            raise ValueError(f"Path does not exist: {value!r}")

    def serialize(self, value):  # noqa: D102
        # as_posix() ensures forward slashes on all platforms; str() would
        # produce backslashes on Windows, breaking cross-platform round-trips.
        return value.as_posix()

    def deserialize(self, value):  # noqa: D102
        return pathlib.Path(value)

    def from_string(self, s):  # noqa: D102
        return pathlib.Path(s)

    def to_string(self, value):  # noqa: D102
        return str(value)

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["metavar"] = "PATH"
        return kwargs


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

    def from_string(self, s):  # noqa: D102
        if s.lower() in ("none", "null", ""):
            return None
        try:
            return int(s)
        except ValueError as err:
            raise ValueError(
                f"Cannot parse {s!r} as seed (env var {self.env!r}). "
                f"Use an integer or 'none'."
            ) from err

    def validate(self, value):  # noqa: D102
        if value is not None and not isinstance(value, int):
            raise TypeError(
                f"Expected an int or None for a seed value, "
                f"got {type(value).__name__!r}"
            )

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["metavar"] = "INT|none"
        return kwargs


class Range(ConfigField):
    """A field for a linear (min, max) numeric range.

    Stores a two-element tuple ``(min, max)`` and validates that
    ``min < max``. This field is intentionally limited to linear ranges.
    Cyclical or angular ranges (e.g. 350 deg to 10 deg crossing zero) are out
    of scope because their validation depends on domain-specific conventions.

    Parameters
    ----------
    default_value : `tuple[numbers.Number, numbers.Number]` or `callable`
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

    def normalize(self, value):  # noqa: D102
        # Coerce list -> tuple: YAML deserializes sequences as lists.
        if isinstance(value, list):
            return tuple(value)
        return value

    def serialize(self, value):  # noqa: D102
        return list(value)

    def deserialize(self, value):  # noqa: D102
        if isinstance(value, list):
            return tuple(value)
        return value

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["metavar"] = "MIN,MAX"
        return kwargs

    def from_string(self, s):  # noqa: D102
        parts = s.split(",")

        if len(parts) != 2:
            raise ValueError(
                f"Cannot parse {s!r} as range (env var {self.env!r}). "
                f"Expected 'min,max' (e.g. '0.0,1.0')."
            )

        def _num(x):
            x = x.strip()
            try:
                return int(x)
            except ValueError:
                try:
                    return float(x)
                except ValueError as err:
                    raise ValueError(
                        f"Cannot parse {s!r} as range (env var {self.env!r}). "
                        f"Expected 'min,max' (e.g. '0.0,1.0')."
                    ) from err

        return (_num(parts[0]), _num(parts[1]))

    def validate(self, value):  # noqa: D102
        try:
            lo, hi = value
        except (TypeError, ValueError) as err:
            raise TypeError(
                f"Expected a (min, max) pair, got {value!r}"
            ) from err
        if not (
            isinstance(lo, numbers.Number) and isinstance(hi, numbers.Number)
        ):  # noqa: E501
            raise TypeError(
                f"Range bounds must be numeric, got {lo!r} and {hi!r}"
            )  # noqa: E501
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
        env=None,
        transient=None,
    ):
        self.element_type = element_type
        self.minlen = minlen
        self.maxlen = maxlen
        super().__init__(
            default_value,
            doc,
            static=static,
            env=env,
            transient=transient,
        )

    def normalize(self, value):  # noqa: D102
        # Coerce tuple -> list: click's multiple=True returns a tuple.
        if isinstance(value, tuple):
            return list(value)
        return value

    def serialize(self, value):  # noqa: D102
        return list(value)

    def deserialize(self, value):  # noqa: D102
        return list(value) if not isinstance(value, list) else value

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["nargs"] = "+"
        kwargs["type"] = (
            self.element_type if self.element_type is not None else str
        )
        return kwargs

    def to_click_option(self, name, prefix=""):  # noqa: D102
        if _click is None:
            raise ImportError(
                "click is required for click_options(). "
                "Install it with: pip install click"
            )
        hyphenated = name.replace("_", "-")
        flag = f"--{prefix}.{hyphenated}" if prefix else f"--{hyphenated}"
        param_name = f"{prefix.replace('.', '__')}__{name}" if prefix else name
        et = self.element_type if self.element_type is not None else str
        return _click.option(
            flag,
            param_name,
            type=et,
            multiple=True,
            default=None,
            help=self.doc,
            show_default=False,
        )

    def from_string(self, s):  # noqa: D102
        try:
            result = json.loads(s)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        return [item.strip() for item in s.split(",") if item.strip()]

    def validate(self, value):  # noqa: D102
        if not isinstance(value, list):
            raise TypeError(f"Expected a list, got {type(value).__name__!r}")
        if self.minlen is not None and len(value) < self.minlen:
            raise ValueError(
                f"Expected at least {self.minlen} elements, got {len(value)}"
            )
        if self.maxlen is not None and len(value) > self.maxlen:
            raise ValueError(
                f"Expected at most {self.maxlen} elements, got {len(value)}"
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

    def from_string(self, s):  # noqa: D102
        try:
            return json.loads(s)
        except (json.JSONDecodeError, ValueError) as err:
            raise ValueError(
                f"Cannot parse {s!r} as JSON dict (env var {self.env!r})"
            ) from err

    def to_string(self, value):  # noqa: D102
        return json.dumps(value)

    def validate(self, value):  # noqa: D102
        if not isinstance(value, dict):
            raise TypeError(f"Expected a dict, got {type(value).__name__!r}")

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["metavar"] = "JSON"
        return kwargs


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

    def normalize(self, value):  # noqa: D102
        # Coerce ISO string -> datetime.date for round-trips through to_dict.
        if isinstance(value, str):
            return datetime.date.fromisoformat(value)
        return value

    def validate(self, value):  # noqa: D102
        if not isinstance(value, datetime.date):
            raise TypeError(
                f"Expected a datetime.date, got {type(value).__name__!r}"
            )

    def serialize(self, value):  # noqa: D102
        return value.isoformat()

    def deserialize(self, value):  # noqa: D102
        if isinstance(value, str):
            return datetime.date.fromisoformat(value)
        return value

    def from_string(self, s):  # noqa: D102
        try:
            return datetime.date.fromisoformat(s)
        except ValueError as err:
            raise ValueError(
                f"Cannot parse {s!r} as ISO date (env var {self.env!r})"
            ) from err

    def to_string(self, value):  # noqa: D102
        return value.isoformat()

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["metavar"] = "YYYY-MM-DD"
        return kwargs


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

    def normalize(self, value):  # noqa: D102
        # Coerce ISO string -> datetime.time: to_dict serializes time as an
        # ISO string (YAML has no native time type), so from_dict round-trips
        # through here.
        if isinstance(value, str):
            return datetime.time.fromisoformat(value)
        return value

    def validate(self, value):  # noqa: D102
        if not isinstance(value, datetime.time):
            raise TypeError(
                f"Expected a datetime.time, got {type(value).__name__!r}"
            )

    def serialize(self, value):  # noqa: D102
        return value.isoformat()

    def deserialize(self, value):  # noqa: D102
        if isinstance(value, str):
            return datetime.time.fromisoformat(value)
        return value

    def from_string(self, s):  # noqa: D102
        try:
            return datetime.time.fromisoformat(s)
        except ValueError as err:
            raise ValueError(
                f"Cannot parse {s!r} as ISO time (env var {self.env!r})"
            ) from err

    def to_string(self, value):  # noqa: D102
        return value.isoformat()

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["metavar"] = "HH:MM:SS"
        return kwargs


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

    def normalize(self, value):  # noqa: D102
        if isinstance(value, str):
            return datetime.datetime.fromisoformat(value)
        return value

    def validate(self, value):  # noqa: D102
        if not isinstance(value, datetime.datetime):
            raise TypeError(
                f"Expected a datetime.datetime, got {type(value).__name__!r}"
            )

    def serialize(self, value):  # noqa: D102
        return value.isoformat()

    def deserialize(self, value):  # noqa: D102
        if isinstance(value, str):
            return datetime.datetime.fromisoformat(value)
        return value

    def from_string(self, s):  # noqa: D102
        try:
            return datetime.datetime.fromisoformat(s)
        except ValueError as err:
            raise ValueError(
                f"Cannot parse {s!r} as ISO datetime (env var {self.env!r})"
            ) from err

    def to_string(self, value):  # noqa: D102
        return value.isoformat()

    def to_argparse_kwargs(self, name, prefix=""):  # noqa: D102
        kwargs = super().to_argparse_kwargs(name, prefix)
        kwargs["metavar"] = "YYYY-MM-DDTHH:MM:SS"
        return kwargs


#############################################################################
# Alias descriptor
#############################################################################


class Alias:
    """A view field that delegates reads and writes to a dotpath on the
    bound config.

    Declare `Alias` attributes on a `ConfigView` subclass to define which
    fields of the underlying config are exposed and under what names.  The
    argument is either a `FieldRef` obtained by class-level attribute access
    on a `Config` class, or a plain dotpath string::

        class CalibSummaryView(ConfigView):
            psf_kernel = Alias(PSFFittingConfig.kernel_estimate)  # preferred
            threshold  = Alias("detection.threshold")              # also works

    Parameters
    ----------
    ref : `FieldRef` or `str`
        Path to the target field on the bound config.  Pass a `FieldRef`
        (from class-level attribute access on a `Config`) to keep the path
        refactorable via IDE rename tools.  A plain dotpath string is
        accepted for convenience.
    """

    def __init__(self, ref):
        self._path = ref._path if isinstance(ref, FieldRef) else ref

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return FieldRef(self.name, None)
        return walk(obj._alias_root, self._path)

    def __set__(self, obj, value):
        walk_set(obj._alias_root, self._path, value)


#############################################################################
# Mirror descriptor
#############################################################################


class Mirror:
    """A config field that keeps multiple dotpaths in sync.

    Declare a ``Mirror`` on a ``Config`` class to enforce that two or more
    fields always hold the same value.  A write fans out to every path; a
    read asserts all paths agree and returns the shared value::

        class SyncedConfig(Config, components=[CameraConfig, DetectorConfig]):
            gain = Mirror(CameraConfig.gain, DetectorConfig.gain)

    Parameters
    ----------
    *refs : `FieldRef` or `str`
        Dotpaths (relative to the config instance) that must stay in sync.
        Pass `FieldRef` objects obtained from class-level attribute access on
        a ``Config`` for refactorable, IDE-navigable paths.
    """

    def __init__(self, *refs):
        self._paths = [r._path if isinstance(r, FieldRef) else r for r in refs]

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return FieldRef(self.name, None)
        values = [walk(obj, p) for p in self._paths]
        if len(set(values)) > 1:
            raise ValueError(
                f"Mirror {self.name!r} paths disagree: "
                f"{dict(zip(self._paths, values, strict=True))}"
            )
        return values[0]

    def __set__(self, obj, value):
        for p in self._paths:
            walk_set(obj, p, value)
