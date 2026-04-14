"""Core Config class and its metaclass.

This module provides `ConfigMeta`, the metaclass that collects descriptor
fields at class-definition time, and `Config`, the base class that all
user-defined configuration classes inherit from.
"""

from .config_field import ConfigField


class ConfigMeta(type):
    """`Config` metaclass that collects field descriptors at class creation.

    At class-definition time, `ConfigMeta` inspects the class body and all
    bases in MRO order to build a ``defaults`` dict that maps field names to
    their `ConfigField` descriptors. This dict is attached to the new class
    and drives iteration, serialization, and display.

    Two composition modes are supported, selected via the ``method`` keyword
    on the class definition:

    ``"unroll"`` (default)
        Fields from all ``components`` and base classes are merged into one
        flat namespace on the new class. Later entries override earlier ones.

    ``"nested"``
        Each component is instantiated as a sub-object and stored under its
        ``shortname`` attribute. The parent class itself holds no flat fields
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
        """Instantiate component configs and key them by ``shortname``.

        Parameters
        ----------
        components : `list` of `Config` or `None`
            Classes to instantiate as sub-config objects.

        Returns
        -------
        `dict`
            Mapping of ``shortname`` to instantiated `Config` object.
        """
        nested = {}
        if components is None:
            return nested
        for comp in reversed(components):
            instance = comp()
            nested[instance.shortname] = instance
        return nested

    def __new__(cls, cls_name, bases, attrs, **kwargs):
        cls_fields = {k: v for k, v in attrs.items() if isinstance(v, ConfigField)}
        components = kwargs.pop("components", None)
        method = kwargs.pop("method", "unroll")

        if "nest" in method:
            nested = cls._nest_configs(components)
            attrs["defaults"] = {}
            attrs.update(nested)
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

    Examples
    --------
    >>> from pyconf import Config, Float, Options
    >>> class SearchConfig(Config):
    ...     shortname = "search"
    ...     n_sigma = Float(5.0, "Detection threshold in sigma", minval=0.0)
    ...     method = Options(("DBSCAN", "RANSAC"), "Clustering algorithm")
    >>> cfg = SearchConfig()
    >>> cfg.n_sigma
    5.0
    >>> cfg.n_sigma = 3.0
    >>> cfg["method"] = "RANSAC"
    >>> print(cfg)  # doctest: +SKIP
    SearchConfig
    --------+-------+------------------------
    Key     | Value | Description
    --------+-------+------------------------
    n_sigma | 3.0   | Detection threshold ...
    method  | RANSAC| Clustering algorithm
    """

    shortname = "conf"

    def __init__(self, **kwargs):
        for k, v in self.defaults.items():
            if not isinstance(v, Config) and not getattr(type(self), k).static:
                setattr(self, k, v.defaultval if not callable(v.defaultval) else v.defaultval)
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
        >>> class SearchConfig(Config):
        ...     n_sigma = Float(5.0, "threshold")
        ...     method = Options(("DBSCAN", "RANSAC"), "algorithm")
        ...
        ...     def validate(self):
        ...         if self.method == "RANSAC" and self.n_sigma > 10:
        ...             raise ValueError("RANSAC requires n_sigma <= 10")
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
        >>> base = SearchConfig()
        >>> fast = base.copy(n_sigma=3.0, method="RANSAC")
        """
        new = self.__class__.__new__(self.__class__)
        for k, v in self.items():
            setattr(new, k, v)
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
            sub-objects are serialized recursively.
        """
        result = {}
        for k, v in self.items():
            result[k] = v.to_dict() if isinstance(v, Config) else v
        return result

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
        instance = cls.__new__(cls)
        for k, v in mapping.items():
            if k not in instance.defaults:
                if strict:
                    raise KeyError(f"Unknown field {k!r} for {cls.__name__!r}")
                continue
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
        return tomli_w.dumps(self.to_dict())

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
    def _make_table(rows):
        """Format rows as a plain-text table with three columns.

        Parameters
        ----------
        rows : `list` of `tuple`
            Each tuple is ``(key, value, description)``.

        Returns
        -------
        `str`
            A fixed-width table string.
        """
        header = ("Key", "Value", "Description")
        all_rows = [header] + list(rows)
        widths = [max(len(str(r[i])) for r in all_rows) for i in range(3)]
        sep = "-+-".join("-" * w for w in widths)
        fmt = lambda r: " | ".join(str(r[i]).ljust(widths[i]) for i in range(3))
        lines = [fmt(header), sep] + [fmt(r) for r in rows]
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
        rows = self._table_rows()
        header = f"{self.__class__.__name__}:"
        if self.__class__.__doc__:
            header += f"\n{self.__class__.__doc__.strip()}"
        return header + "\n" + self._make_table(rows)

    def __repr__(self):
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
        rows_html = "".join(
            f"<tr><td><code>{k}</code></td>"
            f"<td><code>{getattr(self, k)!r}</code></td>"
            f"<td>{getattr(type(self), k).doc}</td></tr>"
            for k in self.keys()
        )
        title = self.__class__.__name__
        doc = f"<p>{self.__class__.__doc__.strip()}</p>" if self.__class__.__doc__ else ""
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
