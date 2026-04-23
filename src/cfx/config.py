"""Core Config class.

This module provides `Config`, the base class that all user-defined
configuration classes inherit from.  Field collection and component wiring
happen in `Config.__init_subclass__`, which runs at class-definition time for
every subclass.
"""

import functools
import pathlib
from typing import ClassVar

from .display import as_inline_string, as_table

try:
    import yaml
except ImportError:
    yaml = None

import typing
import warnings

from .cli import _CLI_UNSET
from .refs import ComponentRef
from .types import ConfigField, FieldSpec, resolve_field_spec

__all__ = ["Config", "FrozenConfigError"]


class FrozenConfigError(AttributeError):
    """Raised when attempting to set a field on a frozen `Config` instance.

    Inherits from `AttributeError` so that standard attribute-protection
    machinery recognises it correctly.
    """


class Config:
    """Base class for all user-defined configuration classes.

    Subclass `Config` and declare `ConfigField` instances as class attributes
    to define a configuration schema. Fields are validated on assignment,
    self-documenting via ``__str__``, and composable via inheritance or the
    ``components=`` keyword.

    Parameters
    ----------
    **kwargs : `object`
        Initial field values passed as keyword arguments. Each keyword must
        match a declared field name and is validated on assignment.

    Attributes
    ----------
    confid : `str`
        Identifier for this config class. Used as the dict key in nested
        serialization and as the attribute name under which this config is
        accessible on a parent config in nested composition mode.
        Defaults to the lowercased class name when not explicitly set, so
        ``class SearchConfig(Config)`` gets ``confid = "searchconfig"``
        automatically.

    Examples
    --------
    >>> from pyconf import Config, Float, Options
    >>> class BaseConfig(Config):
    ...     confid  = "base"
    ...     field1  = Float(5.0, "A float field", minval=0.0)
    ...     field2  = Options(("opt_a", "opt_b"), "An options field")
    >>> cfg = BaseConfig()
    >>> cfg.field1
    5.0
    >>> cfg.field1 = 3.0
    >>> cfg["field2"] = "opt_b"
    >>> print(cfg)  # doctest: +SKIP
    BaseConfig:
    Key    | Value | Description
    -------+-------+----------------
    field1 | 3.0   | A float field
    field2 | opt_b | An options field
    """

    confid: str = "config"
    """Name of this config class when it's used as a component config.
    Automatically set as the lowercase version of the class name.
    """

    _fields: ClassVar[dict[str, ConfigField]] = {}
    """Mapping of field name to descriptor."""

    _nested_classes: ClassVar[dict[str, type]] = {}
    """Mapping of confid to component Config class."""

    def __init_subclass__(cls, components=None, **kwargs):
        super().__init_subclass__(**kwargs)

        if "confid" not in vars(cls):
            cls.confid = cls.__name__.lower()

        own_fields = {
            k: v for k, v in vars(cls).items() if isinstance(v, ConfigField)
        }

        # Resolve annotation-native Field() declarations
        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            hints = getattr(cls, "__annotations__", {})
        for attr_name, value in list(vars(cls).items()):
            if isinstance(value, FieldSpec):
                hint = hints.get(attr_name)
                if hint is None:
                    raise TypeError(
                        f"{cls.__name__}.{attr_name}: "
                        "Field() requires a type annotation"
                    )
                descriptor = resolve_field_spec(attr_name, value, hint)
                descriptor.__set_name__(cls, attr_name)
                setattr(cls, attr_name, descriptor)
                own_fields[attr_name] = descriptor

        # Collect inherited fields first, regardless of composition mode.
        # Fixes the bug where components= discarded parent fields.
        inherited: dict[str, ConfigField] = {}
        for base in reversed(cls.__bases__):
            if hasattr(base, "_fields"):
                inherited.update(base._fields)

        if components is not None:
            seen: set[str] = set()
            dupes: set[str] = set()
            for comp in components:
                (dupes if comp.confid in seen else seen).add(comp.confid)
            if dupes:
                raise ValueError(f"Duplicate confids in components: {dupes}")
            cls._nested_classes = {c.confid: c for c in components}
            for confid, nested_cls in cls._nested_classes.items():
                setattr(cls, confid, ComponentRef(confid, nested_cls))
        else:
            cls._nested_classes = {}

        cls._fields = {**inherited, **own_fields}

    def __init__(self, **kwargs):
        # Nested mode: instantiate each component class fresh so that different
        # parent instances do not share the same sub-config objects.
        for confid, sub_cls in type(self)._nested_classes.items():
            setattr(self, confid, sub_cls())

        # Pre-populate non-static, non-callable fields so every instance has
        # an explicit value in __dict__. Callable defaults and env-var fields
        # are left unset so ConfigField.__get__ evaluates them lazily.
        for k, v in self._fields.items():
            if (
                not v.static
                and not callable(v.defaultval)
                and v.env is None
                and not v.transient
            ):
                setattr(self, k, v.defaultval)

        # now set any kwargs explicitly given through init
        for k, v in kwargs.items():
            setattr(self, k, v)

    ###########################################################################
    #                The may-need-to-be-reimplemented methods
    ###########################################################################
    def validate(self):
        """Validate cross-field constraints.

        The base implementation is a no-op. Override in subclasses to add
        validation logic that involves more than one field. Called
        automatically after deserialization via `from_dict`, `from_yaml`,
        and `from_toml`.

        Raises
        ------
        ValueError
            If any cross-field constraint is violated.

        Examples
        --------
        >>> class BandConfig(Config):
        ...     low  = Float(1.0, "Lower bound", minval=0.0)
        ...     high = Float(2.0, "Upper bound", minval=0.0)
        ...
        ...     def validate(self):
        ...         if self.high <= self.low:
        ...             raise ValueError("high must be greater than low")
        """

    ###########################################################################
    #                    Dunder methods
    ###########################################################################
    def __str__(self):
        return as_table(self, format="text")

    def __repr__(self):
        return as_inline_string(self)

    def _repr_html_(self):
        return as_table(self, format="html")

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False) and (
            name in self._fields or name in type(self)._nested_classes
        ):
            raise FrozenConfigError(f"Cannot set {name!r} on a frozen config.")
        super().__setattr__(name, value)

    def __getitem__(self, key):
        nested_classes = type(self)._nested_classes
        if key in self._fields or key in nested_classes:
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key not in self._fields:
            raise KeyError(key)
        setattr(self, key, value)

    def __iter__(self):
        return iter(self._fields)

    def __contains__(self, key):
        return key in self._fields or key in getattr(
            type(self), "_nested_classes", {}
        )  # noqa: E501

    def __eq__(self, other):
        if not isinstance(other, Config):
            return NotImplemented
        if dict(self.items()) != dict(other.items()):
            return False
        nested_classes = type(self)._nested_classes
        return all(
            getattr(self, c) == getattr(other, c) for c in nested_classes
        )

    ###########################################################################
    #                    Dict/Set-like methods
    ###########################################################################

    def keys(self):
        """Return a set-like object providing a view on the dict's keys."""
        return self._fields.keys()

    def values(self):
        """Return the current values of all declared fields.

        Returns
        -------
        values : `list`
            Current field values in declaration order.
        """
        return [getattr(self, k) for k in self.keys()]

    def items(self):
        """Return (name, value) pairs for all declared fields.

        Returns
        -------
        pairs : `list[tuple]`
            ``(field_name, current_value)`` pairs in declaration order.
        """
        return [(k, getattr(self, k)) for k in self.keys()]

    def update(self, mapping):
        """Set multiple field values from a mapping.

        Each key-value pair is set via ``setattr``, routing through the
        descriptor's ``validate`` method. Nested sub-configs can be updated
        by passing the confid as the key with a ``dict`` value (which is
        applied recursively) or a `Config` instance (which replaces the
        sub-config entirely).

        Parameters
        ----------
        mapping : `dict`
            Field names and their new values. Nested confids are accepted
            with a ``dict`` or `Config` value.

        Raises
        ------
        KeyError
            If any key in ``mapping`` is not a declared field or nested confid.
        TypeError
            If a nested confid key is given a value that is neither a ``dict``
            nor a `Config` instance.
        """
        nested_classes = type(self)._nested_classes
        for k, v in mapping.items():
            if k in self._fields:
                setattr(self, k, v)
            elif k in nested_classes:
                sub = getattr(self, k)
                if isinstance(v, dict):
                    sub.update(v)
                elif isinstance(v, Config):
                    setattr(self, k, v)
                else:
                    raise TypeError(
                        f"Expected dict or Config for nested key {k!r}, "
                        f"got {type(v).__name__!r}"
                    )
            else:
                raise KeyError(k)
        self.validate()

    def freeze(self):
        """Make this config instance read-only.

        After calling `freeze`, any attempt to set a field or replace a
        nested sub-config raises `FrozenConfigError`. The freeze propagates
        recursively to all nested sub-configs.
        """
        object.__setattr__(self, "_frozen", True)
        for confid in type(self)._nested_classes:
            getattr(self, confid).freeze()

    def diff(self, other):
        """Return fields that differ between this config and another.

        Recurses into nested sub-configs. Keys for nested differences use
        dot notation: ``"search.n_sigma"``.

        Parameters
        ----------
        other : `Config`
            Another config instance of the same class to compare against.

        Returns
        -------
        diffs : `dict`
            Mapping of field name (or ``"confid.field"``) to
            ``(self_value, other_value)`` for every field whose value differs.

        Raises
        ------
        TypeError
            If ``other`` is not the same type as this config.
        """
        if type(other) is not type(self):
            raise TypeError(
                f"Cannot diff {type(self).__name__!r} with {type(other).__name__!r}"  # noqa: E501
            )
        result = {}
        for key in self._fields:
            a, b = getattr(self, key), getattr(other, key)
            if a != b:
                result[key] = (a, b)
        for confid in type(self)._nested_classes:
            sub = getattr(self, confid).diff(getattr(other, confid))
            for k, v in sub.items():
                result[f"{confid}.{k}"] = v
        return result

    def copy(self, **overrides):
        """Return a new instance with optionally overridden field values.

        Parameters
        ----------
        **overrides : `object`
            Field names and replacement values applied after copying all
            current field values.

        Returns
        -------
        cfg : `Config`
            A new instance of the same class with the same field values,
            except where overridden.

        Examples
        --------
        >>> base = BaseConfig()
        >>> modified = base.copy(field1="new", field2=9.9)
        """
        new = self.__class__.__new__(self.__class__)

        # Initialize nested sub-configs on the new instance first.
        for confid, _ in type(self)._nested_classes.items():
            setattr(new, confid, getattr(self, confid).copy())

        for k in self.keys():
            descriptor = type(self)._fields[k]
            if descriptor.static:
                continue
            # Only copy fields that have an explicitly stored value in __dict__
            # If missing from __dict__ means it has a callable default.
            # Skip them here allowing the copy to inherit the descriptors
            # factory and recompute lazily from the copy's own field values
            # I can't see how, but there's no way this won't have consequences
            # at some point
            if descriptor.is_set(self):
                setattr(new, k, self.__dict__[descriptor.private_name])

        for k, v in overrides.items():
            setattr(new, k, v)

        return new

    ###########################################################################
    #                    Serialization
    ###########################################################################
    @classmethod
    def from_dict(cls, mapping, strict=True):
        """Create an instance from a plain `dict`.

        Parameters
        ----------
        mapping : `dict`
            Field names and values.
        strict : `bool`, optional
            If `True` (default), raises `KeyError` for any key in ``mapping``
            that is not a declared field. If `False`, unknown keys are silently
            ignored, which is useful when loading configs saved by an older
            version of the class.

        Returns
        -------
        cfg : `Config`
            A new instance with values from ``mapping``.

        Raises
        ------
        KeyError
            If ``strict`` is `True` and ``mapping`` contains an undeclared
            field name.
        """
        stored_ver = mapping.get("_version")
        cls_ver = vars(cls).get("_version")
        version_mismatch = (
            stored_ver is not None
            and cls_ver is not None
            and stored_ver != cls_ver
        )
        if version_mismatch:
            warnings.warn(
                f"Loading {cls.__name__!r} from schema version "
                f"{stored_ver!r}, but class declares version {cls_ver!r}.",
                UserWarning,
                stacklevel=2,
            )

        nested_classes = cls._nested_classes
        instance = cls()
        for k, v in mapping.items():
            if k == "_version":
                continue
            if k in nested_classes:
                continue
            if k not in cls._fields:
                if strict:
                    raise KeyError(f"Unknown field {k!r} for {cls.__name__!r}")
                continue
            descriptor = cls._fields[k]
            if not descriptor.static:
                setattr(instance, k, descriptor.deserialize(v))
        for confid, sub_cls in nested_classes.items():
            sub_dict = mapping.get(confid, {})
            setattr(
                instance, confid, sub_cls.from_dict(sub_dict, strict=strict)
            )
        instance.validate()
        return instance

    def to_dict(self):
        """Serialize this config to a plain `dict`.

        Returns
        -------
        d : `dict`
            Mapping of field names to their current values. Nested `Config`
            sub-objects are serialized recursively. `pathlib.Path` values are
            serialized as strings so the result is always JSON/YAML/TOML-safe.

        """
        nested_classes = type(self)._nested_classes
        result = {}
        for k in self.keys():
            descriptor = type(self)._fields[k]
            if not descriptor.is_set(self) and descriptor.transient:
                continue
            result[k] = descriptor.serialize(getattr(self, k))
        for confid in nested_classes:
            result[confid] = getattr(self, confid).to_dict()
        if "_version" in vars(type(self)):
            result["_version"] = type(self)._version
        return result

    @classmethod
    def from_yaml(cls, text, strict=True):
        """Create an instance from a YAML string.

        Parameters
        ----------
        text : `str`
            YAML-encoded config.
        strict : `bool`, optional
            Passed to `from_dict`. Default is `True`.

        Returns
        -------
        cfg : `Config`
            A new instance with values from the YAML.

        Raises
        ------
        ImportError
            If ``pyyaml`` is not installed.
        """
        if yaml is None:
            raise ImportError(
                "YAML support requires pyyaml. "
                "Install it with: pip install pyyaml"
            )
        return cls.from_dict(yaml.safe_load(text), strict=strict)

    def to_yaml(self):
        """Serialize this config to a YAML string.

        Returns
        -------
        yaml_str : `str`
            YAML representation of the config.

        Raises
        ------
        ImportError
            If ``pyyaml`` is not installed.
        """
        if yaml is None:
            raise ImportError(
                "YAML support requires pyyaml. "
                "Install it with: pip install pyyaml"
            )
        return yaml.dump(
            self.to_dict(), allow_unicode=True, default_flow_style=False
        )

    ###########################################################################
    #                    CLI
    ###########################################################################
    @classmethod
    def add_arguments(cls, parser, prefix=""):
        """Register all non-static fields as arguments on parser.

        For nested configs the component's ``confid`` is used as the
        dot-notation prefix: field ``n_sigma`` in a sub-config with
        ``confid = "search"`` becomes ``--search.n-sigma``.
        An explicit prefix overrides the automatic one, which is useful
        when composing multiple configs into a shared parser manually.

        Parameters
        ----------
        parser : `argparse.ArgumentParser`
            The parser to register arguments on.
        prefix : `str`, optional
            Dot-separated prefix prepended to every flag name. Default ``""``.
        """
        nested_classes = cls._nested_classes

        if not prefix:
            parser.add_argument(
                "config_file",
                nargs="?",
                default=None,
                help="Optional YAML config file. CLI flags override file.",
            )

        for name, descriptor in cls._fields.items():
            if descriptor.static:
                continue
            kwargs = descriptor.to_argparse_kwargs(name, prefix=prefix)
            flag = kwargs.pop("flag")
            parser.add_argument(flag, **kwargs)

        for confid, sub_cls in nested_classes.items():
            sub_prefix = f"{prefix}.{confid}" if prefix else confid
            sub_cls.add_arguments(parser, prefix=sub_prefix)

    @staticmethod
    def _apply_params(instance, params):
        for key, value in params.items():
            # _CLI_UNSET means the flag was not supplied; keep the base value.
            if value is _CLI_UNSET:
                continue
            # Walk the dot path to find the target config and field name.
            if "." in key:
                parts = key.split(".")
                tgtconf = instance
                for part in parts[:-1]:
                    tgtconf = getattr(tgtconf, part)
                field = parts[-1]
            else:
                field = key
                tgtconf = instance
            # Override the value if the field exists and is not static.
            # Unknown keys (f.e. config_file) are silently skipped.
            descriptor = type(tgtconf)._fields.get(field)
            if descriptor is None or descriptor.static:
                continue
            setattr(tgtconf, field, value)

    @classmethod
    def from_argparse(cls, namespace):
        """Build a `Config` instance from a parsed argparse namespace.

        If the namespace contains a ``config_file`` value (registered by
        ``add_arguments``), that file is loaded first and CLI flags are
        applied on top. Without a config file, class-level defaults are
        used as the base.

        Parameters
        ----------
        namespace : `argparse.Namespace`
            Result of ``parser.parse_args()``.

        Returns
        -------
        cfg : `Config`
            A new instance with values taken from the namespace. Fields
            absent from the namespace (value ``None``) keep their base
            defaults.
        """
        params = vars(namespace)
        instance = cls()

        # If provided, load config from file
        config_file = params.get("config_file")
        if config_file is not None:
            p = pathlib.Path(config_file)
            instance = cls.from_yaml(p.read_text())

        # Apply CLI overrides on top
        cls._apply_params(instance, params)
        return instance

    @classmethod
    def _collect_click_options(cls, prefix=""):
        for name, descriptor in cls._fields.items():
            if not descriptor.static:
                yield descriptor.to_click_option(name, prefix=prefix)
        for confid, sub_cls in cls._nested_classes.items():
            sub_prefix = f"{prefix}.{confid}" if prefix else confid
            yield from sub_cls._collect_click_options(sub_prefix)

    @classmethod
    def click_options(cls):
        """Return a decorator that registers all fields as click options.

        Stack on a ``@click.command()`` function::

            @click.command()
            @RunConfig.click_options()
            def run(**kwargs):
                cfg = RunConfig.from_click(kwargs)

        Returns
        -------
        decorator : `callable`
            A decorator that applies all ``click.option`` decorators for this
            config's fields to the target function.

        Raises
        ------
        ImportError
            If ``click`` is not installed.
        """
        try:
            import click  # noqa: F401
        except ImportError as err:
            raise ImportError(
                "click is required for click_options(). "
                "Install it with: pip install click"
            ) from err
        config_file_option = click.option(
            "--config-file",
            default=None,
            help="Optional YAML config file. Other flags override file.",
        )
        options = [config_file_option, *cls._collect_click_options()]

        def decorator(func):
            return functools.reduce(lambda f, o: o(f), reversed(options), func)

        return decorator

    @classmethod
    def from_click(cls, params):
        """Build a `Config` instance from click's ``**kwargs`` dict.

        Pass the kwargs dict received by the decorated command function::

            @click.command()
            @RunConfig.click_options()
            def run(**kwargs):
                cfg = RunConfig.from_click(kwargs)

        Parameters
        ----------
        params : `dict`
            The ``**kwargs`` received by the click-decorated function. Keys
            use double underscores as separators (e.g. ``search__n_sigma``).

        Returns
        -------
        cfg : `Config`
            A new instance with all non-``None`` param values applied.
        """
        instance = cls()

        # Double underscores encode dots in click param names, so translate it
        renamed = {k.replace("__", "."): v for k, v in params.items()}

        # Load from file if provided, otherwise start from class defaults.
        config_file = renamed.pop("config-file", None)
        if config_file is not None:
            p = pathlib.Path(config_file)
            instance = cls.from_yaml(p.read_text())

        # Click uses None as its "option not provided" sentinel. Filter these
        # out before _apply_params so unset click options don't override the
        # base values. (Argparse uses _CLI_UNSET for the same purpose.)
        cls._apply_params(
            instance, {k: v for k, v in renamed.items() if v is not None}
        )
        return instance
