"""Core Config class and its metaclass.

This module provides `ConfigMeta`, the metaclass that collects descriptor
fields at class-definition time, and `Config`, the base class that all
user-defined configuration classes inherit from.
"""

import warnings
import datetime
import pathlib

from .display import as_table, as_inline_string

try:
    import yaml
except ImportError:
    yaml = None

try:
    import tomli_w
except ImportError:
    tomli_w = None

# TODO: this is all a built-in from Py3.11 so we can count on it existing from
# end of 2026 onwards
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from .config_field import ConfigField


__all__ = [
    "Config",
    "FrozenConfigError"
]


class FrozenConfigError(AttributeError):
    """Raised when attempting to set a field on a frozen `Config` instance.

    Inherits from `AttributeError` so that standard attribute-protection
    machinery recognises it correctly.
    """


class ConfigMeta(type):
    """`Config` metaclass that collects field descriptors at class creation.

    At class-definition time, `ConfigMeta` inspects the class body and all
    bases in MRO order to build a ``defaults`` dict that maps field names to
    their `ConfigField` descriptors. This dict is attached to the new class
    and drives iteration, serialization, and display.

    Two composition modes are supported, selected via the ``method`` keyword
    on the class definition:

    ``"unroll"``
        Fields from all ``components`` and base classes are merged into one
        flat namespace on the new class. Later entries override earlier ones.

    ``"nested"`` (default)
        Each component is instantiated as a sub-object and stored under its
        ``confid`` attribute. The parent class itself holds no flat fields
        from the components.

    Parameters
    ----------
    cls_name : `str`
        Name of the class being created.
    bases : `tuple`
        Base classes.
    attrs : `dict`
        Class body attributes.
    components : `list[Config]`, optional
        Additional config classes to compose into this one.
    method : `str`, optional
        Composition method: ``"unroll"`` (default) or ``"nested"``.
    """

    @staticmethod
    def _unroll_defaults(configs):
        """Collect field descriptors from a list of Config classes.

        Parameters
        ----------
        configs : `list[Config]` or `None`
            Classes whose ``defaults`` dicts are merged in reverse order so
            that the first entry wins on conflict.

        Returns
        -------
        conf : `dict`
            Mapping of field name to `ConfigField` descriptor.
        """
        conf = {}
        if configs is None:
            return conf
        for cfg in reversed(configs):
            if hasattr(cfg, "defaults"):
                conf.update(cfg.defaults)
        return conf

    @staticmethod
    def _nest_configs(components):
        """Instantiate component configs and key them by ``confid``.

        Parameters
        ----------
        components : `list[Config]` or `None`
            Classes to instantiate as sub-config objects.

        Returns
        -------
        nested : `dict`
            Mapping of ``confid`` to instantiated `Config` object.
        """
        nested = {}
        if components is None:
            return nested
        for comp in reversed(components):
            instance = comp()
            nested[instance.confid] = instance
        return nested

    def __new__(cls, cls_name, bases, attrs, **kwargs):  # noqa: D102
        cls_fields = {k: v for k, v in attrs.items() if isinstance(v, ConfigField)}  # noqa: E501
        components = kwargs.pop("components", None)
        method = kwargs.pop("method", "nested" if components is not None else "unroll")  # noqa: E501
        if "confid" not in attrs:
            attrs["confid"] = cls_name.lower()

        if "nest" in method:
            # Store component *classes* keyed by confid; instances are created
            # fresh in Config.__init__ so each parent instance gets its own
            # sub-configs rather than sharing class-level objects.
            nested_classes = {}
            if components is not None:
                for comp in reversed(components):
                    nested_classes[comp.confid] = comp
            attrs["_nested_classes"] = nested_classes
            attrs["defaults"] = {}
        else:
            config = cls._unroll_defaults(bases)
            config.update(cls._unroll_defaults(components))
            config.update(cls_fields)
            attrs["defaults"] = config
            attrs.update(config)

        return super().__new__(cls, cls_name, bases, attrs, **kwargs)


class Config(metaclass=ConfigMeta):
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

    confid: str
    """Name of this config class when it's used as a component config.
    Automatically set as the lowercase version of the class name.
    """

    def __init__(self, **kwargs):  # noqa: D107
        # Nested mode: instantiate each component class fresh so that different
        # parent instances do not share the same sub-config objects.
        for confid, sub_cls in getattr(type(self), "_nested_classes", {}).items():  # noqa: E501
            object.__setattr__(self, confid, sub_cls())
        # Flat/unroll/inherited mode: initialize stored values for non-static,
        # non-callable fields. Callable defaults are left unset so that
        # ConfigField.__get__ can evaluate them lazily on first access.
        for k, v in self.defaults.items():
            if not isinstance(v, Config) and not getattr(type(self), k).static:
                if not callable(v.defaultval) and v.env is None:
                    setattr(self, k, v.defaultval)
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
    def __str__(self):  # noqa: D105
        return as_table(self, format="text")

    def __repr__(self):  # noqa: D105
        return as_inline_string(self)

    def _repr_html_(self):  # noqa: D105
        return as_table(self, format="html")

    def __setattr__(self, name, value):  # noqa: D105
        if getattr(self, "_frozen", False) and name in self.defaults:
            raise FrozenConfigError(
                f"Cannot set field {name!r} on a frozen config."
            )
        super().__setattr__(name, value)

    def __getitem__(self, key):  # noqa: D105
        if key not in self.defaults:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key, value):  # noqa: D105
        if key not in self.defaults:
            raise KeyError(key)
        setattr(self, key, value)

    def __contains__(self, key):  # noqa: D105
        return key in self.defaults

    def __eq__(self, other):  # noqa: D105
        if not isinstance(other, Config):
            return NotImplemented
        return dict(self.items()) == dict(other.items())

    ###########################################################################
    #                    Dict/Set-like methods
    ###########################################################################
    def keys(self):
        """Return a set-like object providing a view on the dict's keys."""
        return self.defaults.keys()

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
        descriptor's ``validate`` method.

        Parameters
        ----------
        mapping : `dict`
            Field names and their new values.

        Raises
        ------
        KeyError
            If any key in ``mapping`` is not a declared field.
        """
        for k, v in mapping.items():
            if k not in self.defaults:
                raise KeyError(k)
            setattr(self, k, v)

    def freeze(self):
        """Make this config instance read-only.

        After calling `freeze`, any attempt to set a field raises
        `FrozenConfigError`.
        """
        object.__setattr__(self, "_frozen", True)

    def diff(self, other):
        """Return fields that differ between this config and another.

        Parameters
        ----------
        other : `Config`
            Another config instance of the same class to compare against.

        Returns
        -------
        diffs : `dict`
            Mapping of field name to ``(self_value, other_value)`` for every
            field whose value differs.

        Raises
        ------
        TypeError
            If ``other`` is not the same type as this config.
        """
        if type(other) is not type(self):
            raise TypeError(
                f"Cannot diff {type(self).__name__!r} with {type(other).__name__!r}"  # noqa: E501
            )
        return {
            key: (this, other)
            for (key, this), (_, other) in zip(self.items(), other.items())
            if this != other
        }

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
        for confid, sub_cls in getattr(type(self), "_nested_classes", {}).items():  # noqa: E501
            object.__setattr__(new, confid, getattr(self, confid).copy())
        for k in self.keys():
            descriptor = getattr(type(self), k)
            if descriptor.static:
                continue
            # Only copy fields that have an explicitly stored value in __dict__
            # If missing from __dict__ means it has a callable default.
            # Skip them here allowing the copy to inherit the descriptors
            # factory and recompute lazily from the copy's own field values
            # I can't see how, but there's no way this won't have consequences
            # at some point
            if descriptor.private_name in self.__dict__:
                setattr(new, k, self.__dict__[descriptor.private_name])
        for k, v in overrides.items():
            setattr(new, k, v)
        return new

    ###########################################################################
    #                    Serialization
    ###########################################################################
    @staticmethod
    def _strip_none(d):
        """Recursively remove None values from a dict."""
        return {
            k: (Config._strip_none(v) if isinstance(v, dict) else v)
            for k, v in d.items()
            if v is not None
        }

    @staticmethod
    def _serialize_value(v):
        """Convert a field value to a plain, serializer-safe Python object.

        YAML and TOML serializers cannot handle Python-specific types like
        pathlib.Path, set, frozenset, or tuple natively. We normalize them
        here so that yaml.dump / tomli_w.dumps always receive plain types.
        The reverse coercion (list->tuple, list->set, str->Path) is handled
        by each field's __set__ when from_dict / from_yaml / from_toml
        loads the data back.
        """
        if isinstance(v, Config):
            return v.to_dict()
        if isinstance(v, pathlib.Path):
            # PosixPath / WindowsPath are not YAML/TOML serializable.
            return str(v)
        if isinstance(v, (set, frozenset)):
            # yaml uses !!set (not safe_load-readable); TOML has no set type.
            # Sorting gives deterministic output
            return sorted(v, key=str)
        if isinstance(v, tuple):
            # yaml uses !!python/tuple (not safe_load-readable)
            return list(v)
        if isinstance(v, datetime.time) and not isinstance(v, datetime.datetime):  # noqa: E501
            # datetime.time has no native YAML safe representation.
            return v.isoformat()
        return v

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
        # Nested composition mode: route each sub-dict to its component class.
        nested_classes = getattr(cls, "_nested_classes", {})
        if nested_classes:
            instance = cls.__new__(cls)
            for confid, sub_cls in nested_classes.items():
                sub_dict = mapping.get(confid, {})
                object.__setattr__(
                    instance,
                    confid,
                    sub_cls.from_dict(sub_dict, strict=strict)
                )
            instance.validate()
            return instance

        instance = cls.__new__(cls)
        for k, v in mapping.items():
            if k not in instance.defaults:
                if strict:
                    raise KeyError(f"Unknown field {k!r} for {cls.__name__!r}")
                continue
            if not getattr(cls, k).static:
                setattr(instance, k, v)
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

        Warns
        -----
        UserWarning
            If any field has a callable default and no explicitly stored value.
            The serialized value is a computed snapshot; the formula is lost
            after deserialization.
        """
        # Nested composition mode: iterate sub-configs by confid.
        nested_classes = getattr(type(self), "_nested_classes", {})
        if nested_classes:
            return {
                confid: getattr(self, confid).to_dict()
                for confid in nested_classes
            }

        result = {}
        for k in self.keys():
            descriptor = getattr(type(self), k)
            if callable(descriptor.defaultval) and descriptor.private_name not in self.__dict__:  # noqa: E501
                warnings.warn(
                    f"Field {k!r} is a callable. The serialized value will be "
                    f"a snapshot of its current value, the callable will not "
                    f"survive deserialization.",
                    UserWarning,
                    stacklevel=2,
                )
            v = getattr(self, k)
            result[k] = self._serialize_value(v)
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
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)  # noqa: E501

    @classmethod
    def from_toml(cls, text, strict=True):
        """Create an instance from a TOML string.

        Parameters
        ----------
        text : `str`
            TOML-encoded config.
        strict : `bool`, optional
            Passed to `from_dict`. Default is `True`.

        Returns
        -------
        cfg : `Config`
            A new instance with values from the TOML.

        Raises
        ------
        ImportError
            If neither ``tomllib`` (stdlib, Python >= 3.11) nor ``tomli``
            is available.
        """
        if tomllib is None:
            raise ImportError(
                "TOML read support requires tomli on Python < 3.11. "
                "Install it with: pip install tomli"
            )
        return cls.from_dict(tomllib.loads(text), strict=strict)

    def to_toml(self):
        """Serialize this config to a TOML string.

        Returns
        -------
        toml_str : `str`
            TOML representation of the config.

        Raises
        ------
        ImportError
            If ``tomli-w`` is not installed.
        """
        if tomli_w is None:
            raise ImportError(
                "TOML write support requires tomli-w. "
                "Install it with: pip install tomli-w"
            )
        # TOML has no null type. Strip None values so tomli_w doesn't raise.
        # Fields with None values will be absent from the TOML output and will
        # fall back to their class-level default when loaded — which is correct
        # for fields like Seed(None, ...) where None is the intended default.
        # Now, since this is a config and not a generic data structure that
        # needs to persist values/collections and whatnot, I'm hoping this is
        # never an actual problem and that fields that need None's as defaults
        # just default to None's. But I guess we'll see.
        return tomli_w.dumps(self._strip_none(self.to_dict()))
