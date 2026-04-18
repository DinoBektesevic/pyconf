"""Base descriptor class for self-documenting configuration fields.

This module defines `ConfigField`, which implements the Python descriptor
protocol to provide validated, documented configuration fields that live
directly on `Config` class definitions. Subclass `ConfigField` and override
`ConfigField.validate` to add type or value constraints.
"""

import os

__all__ = ["ConfigField"]


class ConfigField:
    """Base descriptor for a single configuration field.

    Implements ``__get__``, ``__set__``, and ``__set_name__`` so that
    instances assigned as class attributes behave as managed, validated
    attributes on `Config` subclasses.

    The default value may be a plain object or a callable that accepts
    the owning instance as its sole argument (a lazy factory). When a
    lazy factory is provided, the computed value is returned on every
    access until the user explicitly sets the attribute, after which the
    stored value is used instead.

    Parameters
    ----------
    default_value : `object` or `callable`
        Default value for the field. If callable, it is treated as a lazy
        factory: ``default_value(instance)`` is called on each ``__get__``
        invocation until an explicit value is stored on the instance.
    doc : `str`
        Human-readable description shown in ``__str__`` tables and Jupyter
        ``_repr_html_`` output.
    static : `bool`, optional
        If `True` the value is frozen to ``default_value`` at class-definition
        time and cannot be changed on instances. Any attempted ``__set__``
        raises `AttributeError`. Default is `False`.
    env : `str` or `None`, optional
        Name of an environment variable to consult when no explicit value has
        been stored on the instance. When set, the priority chain is:
        explicit assignment > environment variable > default. The raw string
        from ``os.environ`` is coerced by `_from_env_str` and then validated.
        The env value is not stored on the instance - it is re-read on
        every access, matching the behaviour of callable defaults. ``None``
        means no environment variable is consulted. Default is `None`.

    Raises
    ------
    TypeError
        If ``default_value`` (when not callable) fails `validate`.
    ValueError
        If ``default_value`` (when not callable) fails `validate`.

    Examples
    --------
    >>> from pyconf import Config, ConfigField
    >>> class MyConfig(Config):
    ...     name = ConfigField("default", "A simple untyped field")
    >>> cfg = MyConfig()
    >>> cfg.name
    'default'
    >>> cfg.name = "something else"
    >>> cfg.name
    'something else'
    """

    def __init__(
        self,
        default_value,
        doc,
        static=False,
        env=None,
        transient=None,
    ):
        self.defaultval = default_value
        self.doc = doc
        self.static = static
        self.env = env
        self._transient = transient
        if not callable(default_value):
            self.validate(default_value)

    @property
    def transient(self):
        """True when the field is skipped on serialization if no value stored."""  # noqa: E501
        if self._transient is None:
            return callable(self.defaultval)
        return self._transient

    ###########################################################################
    #                The may-need-to-be-reimplemented methods
    # Ideally, I would have made these methods a abc.abstracmethod, but they
    # have very reasonable default implementations so it's not obvious I should
    ###########################################################################
    def from_string(self, s):
        """Parse a raw string into this field's type.

        Override in subclasses to coerce the raw string to the appropriate
        type for a particular `ConfigField`. The default implementation returns
        the unchanged string.

        Called by ``__get__`` when ``env`` is set and the variable is present
        in the environment but the instance has no explicitly stored value, and
        by the CLI integration as the argparse ``type=`` callable. The result
        is then passed to `validate`.

        Parameters
        ----------
        s : `str`
            Raw string value.

        Returns
        -------
        value : `object`
            The coerced value, ready to pass to `validate`.
        """
        return s

    def to_string(self, value):
        """Format a field value as a human-readable string for display.

        Called by the display layer when rendering the config table. Override
        in subclasses to produce cleaner output than Python's default
        ``str()``. The default implementation returns ``str(value)``.

        Parameters
        ----------
        value : `object`
            The current field value.

        Returns
        -------
        s : `str`
            Display string for the value.
        """
        return str(value)

    def validate(self, value):
        """Validate a value against this field's constraints.

        Override in subclasses to enforce correct type or range of values.
        Raise `TypeError` for wrong type, and `ValueError` for out-of-range
        error. The base implementation accepts any value.

        Parameters
        ----------
        value : `object`
            The value to validate.

        Raises
        ------
        TypeError
            If the value has the wrong type.
        ValueError
            If the value is outside the allowed range or set.
        """
        return True

    ###########################################################################
    #                Dunder methods
    ###########################################################################
    def __repr__(self):
        env_part = f", env={self.env!r}" if self.env is not None else ""
        return (
            f"{self.__class__.__name__}("
            f"name={self.public_name!r}, "
            f"default={self.defaultval!r}, "
            f"doc={self.doc!r}"
            f"{env_part})"
        )

    def __str__(self):
        env_part = f", env={self.env!r}" if self.env is not None else ""
        return (
            f"{self.__class__.__name__}("
            f"name={self.public_name!r}, "
            f"default={self.defaultval!r}, "
            f"doc={self.doc!r}"
            f"{env_part})"
        )

    ###########################################################################
    #                Descriptor protocol dunders
    ###########################################################################
    def __set_name__(self, owner, name):
        """Record the attribute name assigned by the owning class.

        Called automatically by the metaclass machinery when the descriptor
        is assigned as a class attribute. Sets `public_name` (the name as
        written in the class body) and `private_name` (the name used to store
        the per-instance value in ``instance.__dict__``).

        Parameters
        ----------
        owner : `type`
            The class that owns this descriptor.
        name : `str`
            The attribute name under which this descriptor was assigned.
        """
        self.public_name = name
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None):
        """Return the field value for the owning instance.

        If accessed on the class (``obj`` is `None`) returns the descriptor
        itself, allowing introspection of field metadata.

        For static fields, always returns `defaultval`.

        For non-static fields with no explicitly stored value, the lookup
        order is:

        - explicit assignment (stored on the instance)
        - environment variable, when `env` is set and the variable is
          present in ``os.environ``
        - ``defaultval``, called if callable, returned directly otherwise

        Parameters
        ----------
        obj : `Config` or `None`
            The owning instance, or `None` when accessed on the class.
        objtype : `type`, optional
            The owning class.

        Returns
        -------
        value : `object`
            The field value, or this descriptor when ``obj`` is `None`.
        """
        if obj is None:
            return self
        if self.static:
            return self.defaultval
        sentinel = object()
        stored = getattr(obj, self.private_name, sentinel)
        if stored is sentinel:
            if self.env is not None:
                raw = os.environ.get(self.env)
                if raw is not None:
                    value = self.from_string(raw)
                    self.validate(value)
                    return value
            if callable(self.defaultval):
                return self.defaultval(obj)
            return self.defaultval
        return stored

    def __set__(self, obj, value):
        """Set the field value on the owning instance after validation.

        Parameters
        ----------
        obj : `Config`
            The owning instance.
        value : `object`
            The new value. Passed through `validate` before being stored.

        Raises
        ------
        AttributeError
            If the field is declared ``static=True``.
        TypeError
            If the value fails `validate`.
        ValueError
            If the value fails `validate`.
        """
        if self.static:
            raise AttributeError("Cannot set a static config field.")
        self.validate(value)
        setattr(obj, self.private_name, value)
