"""Field and component reference proxies.

Accessing a field or component on a `Config` *class* (not an instance)
returns a `FieldRef` that records the dotpath to that attribute.  These
references are passed to `Alias` and `Mirror` at view class definition time
so that paths are validated against the schema immediately, before any
instance exists.

Chaining attribute access extends the path one step at a time::

    CalibrationConfig.psf_fitting.kernel_estimate
    # → FieldRef("psf_fitting.kernel_estimate")
"""

__all__ = ["FieldRef", "ComponentRef"]


class FieldRef:
    """A reference to a field on a `Config` class.

    Obtained by accessing a field or component as a class attribute rather
    than on an instance.  Attribute chains are validated against the schema
    at definition time — a typo in the path raises `AttributeError`
    immediately, not at the first runtime access.

    Pass a `FieldRef` to `Alias` or `Mirror` instead of a plain string to
    keep paths refactorable via normal IDE rename and go-to-definition tools.

    Examples
    --------
    >>> from cfx import Config, Field, Alias
    >>> class Inner(Config):
    ...     x: float = Field(1.0, "x value")
    >>> class Outer(Config, components=[Inner]):
    ...     pass
    >>> Outer.inner.x          # doctest: +ELLIPSIS
    FieldRef(...)
    >>> Alias(Outer.inner.x)   # doctest: +ELLIPSIS
    <...Alias object at ...>
    """

    def __init__(self, path: str, resolved_cls):
        self._path = path
        # None for leaf fields; a Config subclass for component branch nodes.
        self._cls = resolved_cls

    def __getattr__(self, name: str) -> "FieldRef":
        if name.startswith("_"):
            raise AttributeError(name)
        if self._cls is None:
            raise AttributeError(
                f"cannot traverse past leaf field {self._path!r}"
            )
        if name in self._cls._fields:
            return FieldRef(f"{self._path}.{name}", None)
        if name in self._cls._nested_classes:
            return FieldRef(
                f"{self._path}.{name}", self._cls._nested_classes[name]
            )
        raise AttributeError(
            f"{self._cls.__name__!r} has no field or component {name!r}"
        )

    def __repr__(self) -> str:
        return f"FieldRef({self._path!r})"


class ComponentRef:
    """Descriptor installed on a `Config` class for each component slot.

    Installed automatically by `_ConfigType` after ``_nested_classes`` is
    built.  Returns a `FieldRef` on class-level access so component paths
    can be used in `Alias` and `Mirror` declarations.  On instance access
    returns the stored sub-config instance as normal.
    """

    def __init__(self, confid: str, cls):
        self.confid = confid
        self.cls = cls

    def __set_name__(self, owner, name: str):
        self.confid = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return FieldRef(self.confid, self.cls)
        return obj.__dict__[self.confid]
