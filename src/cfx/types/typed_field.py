"""Annotation-native field factory.

``Field()`` is the primary way to declare config fields when you want the
field type inferred automatically from the type annotation::

    class SearchConfig(Config):
        n_sigma: float = Field(5.0, "Detection threshold", ge=0.0)
        method: Literal["DBSCAN", "RANSAC"] = Field("DBSCAN", "Algorithm")

For custom field types or advanced validation, import explicit types from
``cfx.types`` and declare them directly::

    from cfx.types import Float, Options

    class SearchConfig(Config):
        n_sigma = Float(5.0, "Detection threshold", ge=0.0)
        method  = Options(("DBSCAN", "RANSAC"), "Algorithm")
"""

import datetime
import pathlib
import types  # UnionType, support for int|float expressions in Py<3.14
import typing as t

from .types import (
    Any,
    Bool,
    Date,
    DateTime,
    Dict,
    Float,
    Int,
    List,
    MultiOptions,
    Options,
    Path,
    Range,
    Scalar,
    Seed,
    String,
    Time,
)

__all__ = ["Field", "FieldSpec", "resolve_field_spec"]


class FieldSpec:
    """Placeholder returned by ``Field()``; resolved at class-definition time.

    Users should not instantiate this directly — use ``Field()`` instead.
    ``Config.__init_subclass__`` replaces every ``FieldSpec`` with the
    appropriate ``ConfigField`` subclass before any instance is created.
    """

    def __init__(self, default, doc, **kwargs):
        self.default = default
        self.doc = doc
        self.kwargs = kwargs


def Field(default, doc="", **kwargs):
    """Declare an annotation-native config field.

    Use as the right-hand side of a type-annotated class attribute on a
    ``Config`` subclass.  The concrete ``ConfigField`` subclass is inferred
    from the annotation at class-definition time::

        from typing import Literal
        from cfx import Config, Field

        class SearchConfig(Config):
            n_sigma: float = Field(5.0, "Detection threshold", ge=0.0)
            method: Literal["DBSCAN", "RANSAC"] = Field("DBSCAN", "Algorithm")
            verbose: bool = Field(False, "Enable verbose output")

    ``choices=`` is an alternative to ``Literal[...]`` annotations — useful
    when the allowed values are a runtime constant rather than a literal::

        ALGORITHMS = ("DBSCAN", "RANSAC", "IsolationForest")

        class SearchConfig(Config):
            method: str = Field("DBSCAN", "Algorithm", choices=ALGORITHMS)

    Callable defaults are supported for computed fields::

        class DerivedConfig(Config):
            base: float = Field(1.0, "Base value")
            derived: float = Field(lambda self: self.base * 2, "Derived value")

    Parameters
    ----------
    default : `object` or `callable`
        Default value or lazy factory accepting the owning instance.
    doc : `str`, optional
        Human-readable description shown in display tables.
    choices : `tuple`, optional
        Allowed values.  Resolves to :class:`~cfx.Options` (or
        :class:`~cfx.MultiOptions` when the annotation is ``set``).
        Unlike ``Literal[...]``, the choices are not visible to static type
        checkers — invalid assignments are caught at runtime only.
    **kwargs
        Any keyword argument accepted by the resolved field type (e.g. ``ge=``,
    ``le=``, ``gt=``, ``lt=``, ``env=``, ``static=``, ``transient=``).

    Returns
    -------
    spec : `FieldSpec`
        Placeholder resolved to a ``ConfigField`` at class-definition time.
    """
    return FieldSpec(default, doc, **kwargs)


def resolve_field_spec(name, spec, annotation):
    """Instantiate the right ``ConfigField`` subclass for an annotation.

    Called by ``Config.__init_subclass__`` for every ``FieldSpec`` in the
    class body.  Not part of the end-user API but importable for advanced use.

    Parameters
    ----------
    name : `str`
        The attribute name (used in error messages).
    spec : `FieldSpec`
        The placeholder carrying default, doc, and extra kwargs.
    annotation : `type`
        The resolved type annotation for this attribute.

    Returns
    -------
    field : `ConfigField`
        A fully constructed field descriptor.

    Raises
    ------
    TypeError
        If the annotation cannot be mapped to a known ``ConfigField`` type.
    """
    origin = t.get_origin(annotation)
    args = t.get_args(annotation)

    # Final[T] → static=True, unwrap T
    static = spec.kwargs.pop("static", False)
    if origin is t.Final:
        static = True
        annotation = args[0] if args else t.Any
        origin = t.get_origin(annotation)
        args = t.get_args(annotation)
    kw = {"static": static, **spec.kwargs} if static else dict(spec.kwargs)

    # choices= Options / MultiOptions (annotation stays as plain str/set/etc.)
    choices = kw.pop("choices", None)
    if choices is not None:
        if origin is set or annotation is set:
            return MultiOptions(
                choices, spec.doc, default_value=spec.default, **kw
            )
        return Options(choices, spec.doc, default_value=spec.default, **kw)

    # Literal[...] → Options  (Options takes options first, not default)
    if origin is t.Literal:
        return Options(args, spec.doc, default_value=spec.default, **kw)

    # set[Literal[...]] → MultiOptions
    if origin is set and args and t.get_origin(args[0]) is t.Literal:
        return MultiOptions(
            t.get_args(args[0]), spec.doc, default_value=spec.default, **kw
        )

    # list[T] → List
    if origin is list:
        elem = args[0] if args else None
        return List(spec.default, spec.doc, element_type=elem, **kw)

    # tuple[T, T] → Range
    if origin is tuple and len(args) == 2:
        return Range(spec.default, spec.doc, **kw)

    # Union types
    if origin is t.Union or origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and type(None) in args and non_none[0] is int:
            return Seed(spec.default, spec.doc, **kw)
        if set(non_none) == {int, float} and type(None) not in args:
            return Scalar(spec.default, spec.doc, **kw)

    # 1-to-1 map — t.Any avoids shadowing cfx.types.Any defined above
    type_map = {
        bool: Bool,
        int: Int,
        float: Float,
        str: String,
        pathlib.Path: Path,
        datetime.date: Date,
        datetime.time: Time,
        datetime.datetime: DateTime,
        dict: Dict,
        t.Any: Any,
    }
    if annotation in type_map:
        return type_map[annotation](spec.default, spec.doc, **kw)

    raise TypeError(
        f"Cannot infer field type from annotation {annotation!r} "
        f"for {name!r}. Declare the field explicitly using a type from "
        "cfx.types (e.g. Float, Int, Options) or subclass ConfigField."
    )
