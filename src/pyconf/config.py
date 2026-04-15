"""Core Config class and its metaclass.

This module provides `ConfigMeta`, the metaclass that collects descriptor
fields at class-definition time, and `Config`, the base class that all
user-defined configuration classes inherit from.
"""

import warnings
import datetime
import pathlib

from .config_field import ConfigField


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
    components : `list` of `Config` subclasses, optional
        Additional config classes to compose into this one.
    method : `str`, optional
        Composition method: ``"unroll"`` (default) or ``"nested"``.
    """

    @staticmethod
    def _unroll_defaults(configs):
        """Collect field descriptors from a list of Config classes.

        Parameters
        ----------
        configs : `list` of `Config` or `None`
            Classes whose ``defaults`` dicts are merged in reverse order so
            that the first entry wins on conflict.

        Returns
        -------
        `dict`
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
        components : `list` of `Config` or `None`
            Classes to instantiate as sub-config objects.

        Returns
        -------
        `dict`
            Mapping of ``confid`` to instantiated `Config` object.
        """
        nested = {}
        if components is None:
            return nested
        for comp in reversed(components):
            instance = comp()
            nested[instance.confid] = instance
        return nested

    def __new__(cls, cls_name, bases, attrs, **kwargs):
        cls_fields = {k: v for k, v in attrs.items() if isinstance(v, ConfigField)}
        components = kwargs.pop("components", None)
        method = kwargs.pop("method", "nested" if components is not None else "unroll")
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

    def __init__(self, **kwargs):
        # Nested mode: instantiate each component class fresh so that different
        # parent instances do not share the same sub-config objects.
        for confid, sub_cls in getattr(type(self), "_nested_classes", {}).items():
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

    def keys(self):
        """Return the names of all declared fields.

        Returns
        -------
        `collections.abc.KeysView`
            Field names in declaration order.
        """
        return self.defaults.keys()

    def values(self):
        """Return the current values of all declared fields.

        Returns
        -------
        `list`
            Current field values in declaration order.
        """
        return [getattr(self, k) for k in self.keys()]

    def items(self):
        """Return (name, value) pairs for all declared fields.

        Returns
        -------
        `list` of `tuple`
            ``(field_name, current_value)`` pairs in declaration order.
        """
        return [(k, getattr(self, k)) for k in self.keys()]

    def __getitem__(self, key):
        """Return a field value using dict-style access.

        Parameters
        ----------
        key : `str`
            Field name.

        Returns
        -------
        `object`
            Current value of the field.

        Raises
        ------
        KeyError
            If the field name does not exist.
        """
        if key not in self.defaults:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key, value):
        """Set a field value using dict-style access.

        Routes through the descriptor's ``validate`` method exactly as
        dot-access assignment does.

        Parameters
        ----------
        key : `str`
            Field name.
        value : `object`
            New value.

        Raises
        ------
        KeyError
            If the field name does not exist.
        """
        if key not in self.defaults:
            raise KeyError(key)
        setattr(self, key, value)

    def __contains__(self, key):
        """Return whether a field name exists on this config.

        Parameters
        ----------
        key : `str`
            Field name to check.

        Returns
        -------
        `bool`
        """
        return key in self.defaults

    def __eq__(self, other):
        """Return whether two config instances have equal field values.

        Parameters
        ----------
        other : `Config`
            Another config instance to compare against.

        Returns
        -------
        `bool`
            `True` if both configs have identical field values, `False`
            otherwise. Returns `NotImplemented` if ``other`` is not a
            `Config`.
        """
        if not isinstance(other, Config):
            return NotImplemented
        return dict(self.items()) == dict(other.items())

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

    def freeze(self):
        """Make this config instance read-only.

        After calling `freeze`, any attempt to set a field raises
        `FrozenConfigError`.
        """
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False) and name in self.defaults:
            raise FrozenConfigError(
                f"Cannot set field {name!r} on a frozen config."
            )
        super().__setattr__(name, value)

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

    def copy(self, **overrides):
        """Return a new instance with optionally overridden field values.

        Parameters
        ----------
        **overrides : `object`
            Field names and replacement values applied after copying all
            current field values.

        Returns
        -------
        `Config`
            A new instance of the same class with the same field values,
            except where overridden.

        Examples
        --------
        >>> base = BaseConfig()
        >>> modified = base.copy(field1="new", field2=9.9)
        """
        new = self.__class__.__new__(self.__class__)
        # Initialize nested sub-configs on the new instance first.
        for confid, sub_cls in getattr(type(self), "_nested_classes", {}).items():
            object.__setattr__(new, confid, getattr(self, confid).copy())
        for k in self.keys():
            descriptor = getattr(type(self), k)
            if descriptor.static:
                continue
            # Only copy fields that have an explicitly stored value in __dict__.
            # Fields absent from __dict__ have a callable default; skipping them
            # lets the copy inherit the descriptor's factory and recompute lazily
            # from the copy's own field values rather than baking in a snapshot.
            if descriptor.private_name in self.__dict__:
                setattr(new, k, self.__dict__[descriptor.private_name])
        for k, v in overrides.items():
            setattr(new, k, v)
        return new

    def diff(self, other):
        """Return fields that differ between this config and another.

        Parameters
        ----------
        other : `Config`
            Another config instance of the same class to compare against.

        Returns
        -------
        `dict`
            Mapping of field name to ``(self_value, other_value)`` for every
            field whose value differs.

        Raises
        ------
        TypeError
            If ``other`` is not the same type as this config.
        """
        if type(other) is not type(self):
            raise TypeError(
                f"Cannot diff {type(self).__name__!r} with {type(other).__name__!r}"
            )
        return {
            k: (sv, ov)
            for (k, sv), (_, ov) in zip(self.items(), other.items())
            if sv != ov
        }

    def to_dict(self):
        """Serialize this config to a plain `dict`.

        Returns
        -------
        `dict`
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
            # Warn when serializing a callable-default field that has no stored
            # value in __dict__. The round-tripped config will have a plain value
            # instead of the original formula — accessing __dict__ directly is the
            # only reliable way to distinguish "user set this" from "computed lazily".
            if callable(descriptor.defaultval) and descriptor.private_name not in self.__dict__:
                warnings.warn(
                    f"Field {k!r} has a callable default and no stored value. "
                    f"The serialized value is a snapshot; the formula will not "
                    f"survive deserialization.",
                    UserWarning,
                    stacklevel=2,
                )
            v = getattr(self, k)
            result[k] = self._serialize_value(v)
        return result

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
            # yaml.dump uses !!set (not safe_load-readable); TOML has no set type.
            # Sorting gives deterministic output; MultiOptions.__set__ coerces back.
            return sorted(v, key=str)
        if isinstance(v, tuple):
            # yaml.dump uses !!python/tuple (not safe_load-readable).
            # Range.__set__ coerces list → tuple on the way back in.
            return list(v)
        if isinstance(v, datetime.time) and not isinstance(v, datetime.datetime):
            # datetime.time has no native YAML safe representation.
            # Serialize as ISO string; Time.__set__ coerces str back to time.
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
        `Config`
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
                object.__setattr__(instance, confid, sub_cls.from_dict(sub_dict, strict=strict))
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

    def to_yaml(self):
        """Serialize this config to a YAML string.

        Returns
        -------
        `str`
            YAML representation of the config.

        Raises
        ------
        ImportError
            If ``pyyaml`` is not installed.
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "YAML support requires pyyaml. Install it with: pip install pyyaml"
            )
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)

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
        `Config`
            A new instance with values from the YAML.

        Raises
        ------
        ImportError
            If ``pyyaml`` is not installed.
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "YAML support requires pyyaml. Install it with: pip install pyyaml"
            )
        return cls.from_dict(yaml.safe_load(text), strict=strict)

    def to_toml(self):
        """Serialize this config to a TOML string.

        Returns
        -------
        `str`
            TOML representation of the config.

        Raises
        ------
        ImportError
            If ``tomli-w`` is not installed.
        """
        try:
            import tomli_w
        except ImportError:
            raise ImportError(
                "TOML write support requires tomli-w. "
                "Install it with: pip install tomli-w"
            )
        # TOML has no null type. Strip None values so tomli_w doesn't raise.
        # Fields with None values will be absent from the TOML output and will
        # fall back to their class-level default when loaded — which is correct
        # for fields like Seed(None, ...) where None is the intended default.
        return tomli_w.dumps(self._strip_none(self.to_dict()))

    @staticmethod
    def _strip_none(d):
        """Recursively remove None values from a dict for TOML compatibility."""
        return {
            k: (Config._strip_none(v) if isinstance(v, dict) else v)
            for k, v in d.items()
            if v is not None
        }

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
        `Config`
            A new instance with values from the TOML.

        Raises
        ------
        ImportError
            If neither ``tomllib`` (stdlib, Python >= 3.11) nor ``tomli``
            is available.
        """
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ImportError(
                    "TOML read support requires tomli on Python < 3.11. "
                    "Install it with: pip install tomli"
                )
        return cls.from_dict(tomllib.loads(text), strict=strict)

    @staticmethod
    def _make_table(rows, max_key_width=20, max_value_width=25, max_desc_width=50):
        """Format rows as a plain-text table with three columns.

        Long cell values are wrapped at word boundaries so that no column
        exceeds its maximum width. Multi-line rows are padded consistently.

        Parameters
        ----------
        rows : `list` of `tuple`
            Each tuple is ``(key, value, description)``.
        max_key_width : `int`, optional
            Maximum width for the Key column. Default is 20.
        max_value_width : `int`, optional
            Maximum width for the Value column. Default is 25.
        max_desc_width : `int`, optional
            Maximum width for the Description column. Default is 50.

        Returns
        -------
        `str`
            A fixed-width table string.
        """
        import textwrap

        header = ("Key", "Value", "Description")
        max_widths = (max_key_width, max_value_width, max_desc_width)

        def wrap_cell(text, max_w):
            """Wrap text to at most max_w chars, breaking at spaces."""
            lines = textwrap.wrap(str(text), max_w)
            return lines if lines else [""]

        def wrap_row(row):
            return [wrap_cell(str(row[i]), max_widths[i]) for i in range(3)]

        wrapped_header = wrap_row(header)
        wrapped_rows = [wrap_row(r) for r in rows]
        all_wrapped = [wrapped_header] + wrapped_rows

        # Actual column widths from the widest wrapped line in each column.
        widths = [
            max(len(line) for wr in all_wrapped for line in wr[i])
            for i in range(3)
        ]

        sep = "-+-".join("-" * w for w in widths)

        def fmt_row(wrapped_cells):
            n = max(len(c) for c in wrapped_cells)
            out = []
            for i in range(n):
                parts = [
                    (wrapped_cells[col][i] if i < len(wrapped_cells[col]) else "").ljust(widths[col])
                    for col in range(3)
                ]
                out.append(" | ".join(parts))
            return "\n".join(out)

        lines = [fmt_row(wrapped_header), sep] + [fmt_row(wr) for wr in wrapped_rows]
        return "\n".join(lines)

    def _table_rows(self):
        """Return table rows for display.

        Returns
        -------
        `list` of `tuple`
            Each tuple is ``(field_name, current_value, doc_string)``.
        """
        return [
            (k, getattr(self, k), getattr(type(self), k).doc)
            for k in self.keys()
        ]

    def __str__(self):
        nested_classes = getattr(type(self), "_nested_classes", {})
        header = f"{self.__class__.__name__}:"
        if self.__class__.__doc__:
            header += f"\n{self.__class__.__doc__.strip()}"
        if nested_classes:
            sub_tables = "\n\n".join(
                f"[{confid}]\n{getattr(self, confid)}" for confid in nested_classes
            )
            return header + "\n" + sub_tables
        return header + "\n" + self._make_table(self._table_rows())

    def __repr__(self):
        nested_classes = getattr(type(self), "_nested_classes", {})
        if nested_classes:
            pairs = ", ".join(
                f"{confid}={getattr(self, confid)!r}" for confid in nested_classes
            )
        else:
            pairs = ", ".join(f"{k}={getattr(self, k)!r}" for k in self.keys())
        return f"{self.__class__.__name__}({pairs})"

    def _repr_html_(self):
        """Return an HTML table for Jupyter Notebook display.

        Returns
        -------
        `str`
            HTML string containing a styled table of field names, values,
            and descriptions.
        """
        title = self.__class__.__name__
        doc = f"<p>{self.__class__.__doc__.strip()}</p>" if self.__class__.__doc__ else ""
        nested_classes = getattr(type(self), "_nested_classes", {})
        if nested_classes:
            sub_html = "".join(
                getattr(self, confid)._repr_html_() for confid in nested_classes
            )
            return f"<b>{title}</b>{doc}{sub_html}"
        rows_html = "".join(
            f"<tr><td><code>{k}</code></td>"
            f"<td><code>{getattr(self, k)!r}</code></td>"
            f"<td>{getattr(type(self), k).doc}</td></tr>"
            for k in self.keys()
        )
        return (
            f"<b>{title}</b>{doc}"
            f"<table>"
            f"<tr><th>Key</th><th>Value</th><th>Description</th></tr>"
            f"{rows_html}"
            f"</table>"
        )


class FrozenConfigError(AttributeError):
    """Raised when attempting to set a field on a frozen `Config` instance.

    Inherits from `AttributeError` so that standard attribute-protection
    machinery recognises it correctly.
    """
