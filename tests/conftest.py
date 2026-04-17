"""Shared Config class definitions used across the test suite.

All classes defined here follow the same naming conventions as the demo
script: generic names (BaseConfig, ChildConfig, etc.) with numbered fields
to make name-conflict behaviour explicit.
"""

import datetime
import pytest

from cfx import (
    Config,
    ConfigField,
    Any,
    Bool,
    Int,
    Float,
    Scalar,
    String,
    Options,
    MultiOptions,
    Path,
    Seed,
    Range,
    List,
    Dict,
    Date,
    Time,
    DateTime,
)


# ---------------------------------------------------------------------------
# Config class hierarchy used by most tests
# ---------------------------------------------------------------------------

class BaseConfig(Config):
    confid = "base"
    field1 = String("a", "A string field")
    field2 = Float(1.0, "A float field", minval=0.0)
    field3 = Int(10, "An integer field", minval=0)
    field4 = Options(("opt_a", "opt_b", "opt_c"), "An options field")
    field5 = Bool(False, "A boolean flag")
    field6 = Scalar(0.5, "A scalar field")
    seed = Int(42, "A static seed", static=True)


class ExtrasConfig(Config):
    confid = "extras"
    field7 = MultiOptions(("a", "b", "c", "d"), "A multi-options field",
                          default_value={"a", "b"})
    field8 = Path("./output", "A path field")
    field9 = Seed(None, "An RNG seed field")
    field10 = Range((0.0, 1.0), "A linear range field")
    field11 = List([1, 2, 3], "A list field", element_type=int)
    field12 = Dict({}, "A dict field")
    field13 = Any(None, "An unconstrained field")
    field14 = Date(datetime.date(2020, 1, 1), "A date field")
    field15 = Time(datetime.time(12, 0), "A time field")
    field16 = DateTime(
        datetime.datetime(2020, 1, 1, 12, 0), "A datetime field"
    )


class ChildConfig(BaseConfig):
    confid = "child"
    field17 = ConfigField("d", "A field added by ChildConfig.")


class GrandchildConfig(ChildConfig):
    confid = "grandchild"
    field1 = String("overridden", "Overrides BaseConfig.field1.")
    field17 = ConfigField("overridden_too", "Overrides ChildConfig.field17.")


class IndependentConfig(Config):
    confid = "independent"
    field1 = Int(99, "Same name as BaseConfig.field1 but Int, not String.")
    field18 = Float(3.14, "A field not present in any other config.")


class CompoundConfig(
        Config,
        components=[IndependentConfig, GrandchildConfig],
        method="unroll"
):
    """Flat merge of IndependentConfig and GrandchildConfig."""
    pass


class NestedConfig(
        Config,
        components=[IndependentConfig, GrandchildConfig],
        method="nested"
):
    """IndependentConfig and GrandchildConfig nested under their confids."""
    pass


class DeepInnerConfig(Config):
    confid = "inner"
    x = Float(1.0, "inner x")


class DeepMiddleConfig(Config, components=[DeepInnerConfig], method="nested"):
    confid = "middle"
    y = Float(2.0, "middle y")


class DeepOuterConfig(Config, components=[DeepMiddleConfig], method="nested"):
    confid = "outer"


class MixedConfig(Config, components=[DeepInnerConfig], method="nested"):
    confid = "mixed"
    top_field = Float(99.0, "field on the nested container itself")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base():
    return BaseConfig()


@pytest.fixture
def extras():
    return ExtrasConfig()
