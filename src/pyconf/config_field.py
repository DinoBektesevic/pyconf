"""Base descriptor class for self-documenting configuration fields.

This module defines `ConfigField`, which implements the Python descriptor
protocol to provide validated, documented configuration fields that live
directly on `Config` class definitions. Subclass `ConfigField` and override
`ConfigField.validate` to add type or value constraints.
"""

import numbers


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

    def __init__(self, default_value, doc, static=False):
        self.defaultval = default_value
        self.doc = doc
        self.static = static
        if not callable(default_value):
            self.validate(default_value)

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

        For non-static fields with a callable default and no explicitly stored
        value, calls ``defaultval(obj)`` on each access so that changes to
        sibling fields are naturally reflected without caching.

        Parameters
        ----------
        obj : `Config` or `None`
            The owning instance, or `None` when accessed on the class.
        objtype : `type`, optional
            The owning class.

        Returns
        -------
        `object`
            The field value, or this descriptor when ``obj`` is `None`.
        """
        if obj is None:
            return self
        if self.static:
            return self.defaultval
        sentinel = object()
        stored = getattr(obj, self.private_name, sentinel)
        if stored is sentinel:
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

    def validate(self, value):
        """Validate a value against this field's constraints.

        The base implementation accepts any value. Override in subclasses to
        enforce type or range restrictions. Raise `TypeError` for wrong types
        and `ValueError` for out-of-range values.

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

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"name={self.public_name!r}, "
            f"default={self.defaultval!r}, "
            f"doc={self.doc!r})"
        )

    def __str__(self):
        return (
            f"{self.__class__.__name__}("
            f"name={self.public_name!r}, "
            f"default={self.defaultval!r}, "
            f"doc={self.doc!r})"
        )
