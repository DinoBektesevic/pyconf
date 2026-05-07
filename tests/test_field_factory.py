"""Tests for the Field() annotation-native factory and schema versioning."""

import pathlib
import typing
import warnings

import pytest

from cfx import Config, Field
from cfx.types import (
    Any,
    Bool,
    ConfigField,
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
)

###############################################################################
# Helpers
###############################################################################


def _field_type(cfg_cls, name):
    """Return the ConfigField descriptor for *name* on *cfg_cls*."""
    return cfg_cls._fields[name]


###############################################################################
# Annotation → concrete type mapping
###############################################################################


class BasicTypes(Config):
    confid = "basic"
    f: float = Field(1.0, "float field")
    i: int = Field(0, "int field")
    b: bool = Field(False, "bool field")
    s: str = Field("hello", "str field")
    p: pathlib.Path = Field(pathlib.Path("/tmp"), "path field")
    a: typing.Any = Field(None, "any field")


def test_float_inferred():
    assert isinstance(_field_type(BasicTypes, "f"), Float)


def test_int_inferred():
    assert isinstance(_field_type(BasicTypes, "i"), Int)


def test_bool_inferred():
    assert isinstance(_field_type(BasicTypes, "b"), Bool)


def test_str_inferred():
    assert isinstance(_field_type(BasicTypes, "s"), String)


def test_path_inferred():
    assert isinstance(_field_type(BasicTypes, "p"), Path)


def test_any_inferred():
    assert isinstance(_field_type(BasicTypes, "a"), Any)


###############################################################################
# Parametric / compound annotations
###############################################################################


class CompoundTypes(Config):
    confid = "compound"
    mode: typing.Literal["a", "b", "c"] = Field("a", "options field")
    tags: set[typing.Literal["x", "y", "z"]] = Field(set(), "multioptions")
    items: list[int] = Field([], "list field")
    bounds: tuple[float, float] = Field((0.0, 1.0), "range field")
    seed: int | None = Field(None, "seed field")
    numeric: int | float = Field(0, "scalar field")


def test_literal_inferred():
    assert isinstance(_field_type(CompoundTypes, "mode"), Options)


def test_set_literal_inferred():
    assert isinstance(_field_type(CompoundTypes, "tags"), MultiOptions)


def test_list_inferred():
    assert isinstance(_field_type(CompoundTypes, "items"), List)


def test_tuple_inferred():
    assert isinstance(_field_type(CompoundTypes, "bounds"), Range)


def test_optional_int_inferred():
    assert isinstance(_field_type(CompoundTypes, "seed"), Seed)


def test_union_int_float_inferred():
    assert isinstance(_field_type(CompoundTypes, "numeric"), Scalar)


###############################################################################
# Extra kwargs pass through
###############################################################################


class WithKwargs(Config):
    confid = "kwargs"
    x: int = Field(0, "bounded int", ge=0, le=10)
    name: str = Field("default", "bounded str", min_length=1)


def test_kwargs_pass_through_ge():
    cfg = WithKwargs()
    with pytest.raises(ValueError):
        cfg.x = -1


def test_kwargs_pass_through_le():
    cfg = WithKwargs()
    with pytest.raises(ValueError):
        cfg.x = 11


def test_kwargs_pass_through_min_length():
    cfg = WithKwargs()
    with pytest.raises(ValueError):
        cfg.name = ""


###############################################################################
# Final[T] → static=True
###############################################################################


class WithStatic(Config):
    confid = "static"
    version: typing.Final[int] = Field(1, "static version")


def test_final_creates_static():
    assert _field_type(WithStatic, "version").static is True


def test_final_raises_on_set():
    cfg = WithStatic()
    with pytest.raises(AttributeError):
        cfg.version = 2


###############################################################################
# Callable defaults
###############################################################################


class WithCallable(Config):
    confid = "callable"
    base: float = Field(2.0, "base value")
    derived: float = Field(lambda self: self.base * 3, "computed")


def test_callable_default_computed():
    cfg = WithCallable()
    assert cfg.derived == 6.0


def test_callable_default_updates_with_base():
    cfg = WithCallable()
    cfg.base = 5.0
    assert cfg.derived == 15.0


def test_callable_default_overridable():
    cfg = WithCallable()
    cfg.derived = 99.0
    assert cfg.derived == 99.0


###############################################################################
# Error cases
###############################################################################


def test_missing_annotation_raises():
    with pytest.raises(TypeError, match="requires a type annotation"):

        class Bad(Config):
            x = Field(0, "no annotation")


def test_unknown_annotation_raises():
    with pytest.raises(TypeError, match="Cannot infer field type"):

        class Bad(Config):
            x: complex = Field(0 + 0j, "unsupported")


###############################################################################
# Runtime behaviour: instances work correctly after Field() resolution
###############################################################################


def test_default_value():
    cfg = BasicTypes()
    assert cfg.f == 1.0
    assert cfg.i == 0
    assert cfg.b is False
    assert cfg.s == "hello"


def test_assignment_and_validation():
    cfg = BasicTypes()
    cfg.f = 3.14
    assert cfg.f == 3.14
    with pytest.raises(TypeError):
        cfg.f = "not a float"


def test_dict_round_trip():
    cfg = BasicTypes()
    cfg.f = 2.5
    cfg.i = 7
    d = cfg.to_dict()
    cfg2 = BasicTypes.from_dict(d)
    assert cfg2.f == 2.5
    assert cfg2.i == 7


def test_field_is_descriptor():
    """Field() must resolve to a ConfigField, not remain a FieldSpec."""
    for name in BasicTypes._fields:
        assert isinstance(BasicTypes._fields[name], ConfigField)


###############################################################################
# Schema versioning
###############################################################################


class Versioned(Config):
    confid = "versioned"
    _version = 2
    x: float = Field(1.0, "x value")


def test_version_in_to_dict():
    cfg = Versioned()
    d = cfg.to_dict()
    assert d["_version"] == 2


def test_version_not_treated_as_field():
    assert "_version" not in Versioned._fields


def test_from_dict_ignores_version_key():
    cfg = Versioned.from_dict({"x": 5.0, "_version": 2})
    assert cfg.x == 5.0


def test_from_dict_warns_on_version_mismatch():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg = Versioned.from_dict({"x": 3.0, "_version": 1})
    assert len(caught) == 1
    assert issubclass(caught[0].category, UserWarning)
    assert "version" in str(caught[0].message).lower()
    assert cfg.x == 3.0


def test_from_dict_no_warning_same_version():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Versioned.from_dict({"x": 3.0, "_version": 2})
    assert len(caught) == 0


def test_no_version_class_no_version_in_dict():
    cfg = BasicTypes()
    d = cfg.to_dict()
    assert "_version" not in d


def test_strict_from_dict_ignores_version_key():
    """_version must not be treated as unknown field under strict=True."""
    cfg = Versioned.from_dict({"x": 2.0, "_version": 2}, strict=True)
    assert cfg.x == 2.0
