"""Round-trip serialization tests for all composition modes and field types."""

import datetime
import pathlib
import warnings
import pytest

from pyconf import (
    Config, ConfigField,
    Any, Bool, Int, Float, Scalar, String,
    Options, MultiOptions, Path, Seed, Range,
    List, Dict, Date, Time, DateTime,
)
from .conftest import (
    BaseConfig, ExtrasConfig, ChildConfig, GrandchildConfig,
    IndependentConfig, CompoundConfig, NestedConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def roundtrip_dict(cls, instance):
    """Serialize instance to dict and reconstruct."""
    return cls.from_dict(instance.to_dict())


def roundtrip_yaml(cls, instance):
    pytest.importorskip("yaml", reason="pyyaml not installed")
    return cls.from_yaml(instance.to_yaml())


def roundtrip_toml(cls, instance):
    pytest.importorskip("tomli_w", reason="tomli-w not installed")
    return cls.from_toml(instance.to_toml())


# ---------------------------------------------------------------------------
# Flat config — dict round-trip, every field type
# ---------------------------------------------------------------------------

class TestDictRoundTripBase:
    def test_base_config_defaults(self):
        assert roundtrip_dict(BaseConfig, BaseConfig()) == BaseConfig()

    def test_base_config_modified(self):
        cfg = BaseConfig()
        cfg.field1 = "hello"
        cfg.field2 = 7.5
        cfg.field3 = 99
        cfg.field4 = "opt_b"
        cfg.field5 = True
        cfg.field6 = 2
        assert roundtrip_dict(BaseConfig, cfg) == cfg

    def test_extras_config_defaults(self):
        assert roundtrip_dict(ExtrasConfig, ExtrasConfig()) == ExtrasConfig()

    def test_path_serialized_as_string(self):
        d = ExtrasConfig().to_dict()
        assert isinstance(d["field8"], str), "Path must serialize as str"

    def test_path_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field8 = "/tmp/results"
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field8 == pathlib.Path("/tmp/results")

    def test_range_round_trips_as_tuple(self):
        cfg = ExtrasConfig()
        cfg.field10 = (0.5, 2.0)
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field10 == (0.5, 2.0)
        assert isinstance(rt.field10, tuple)

    def test_multioptions_round_trips_as_set(self):
        cfg = ExtrasConfig()
        cfg.field7 = {"a", "c"}
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field7 == {"a", "c"}
        assert isinstance(rt.field7, set)

    def test_seed_none_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field9 = None
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field9 is None

    def test_seed_int_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field9 = 12345
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field9 == 12345

    def test_date_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field14 = datetime.date(2024, 6, 15)
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field14 == datetime.date(2024, 6, 15)

    def test_time_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field15 = datetime.time(9, 30)
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field15 == datetime.time(9, 30)

    def test_datetime_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field16 = datetime.datetime(2024, 6, 15, 9, 30)
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field16 == datetime.datetime(2024, 6, 15, 9, 30)

    def test_list_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field11 = [10, 20, 30]
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field11 == [10, 20, 30]

    def test_dict_round_trips(self):
        cfg = ExtrasConfig()
        cfg.field12 = {"key": "value", "n": 42}
        rt = roundtrip_dict(ExtrasConfig, cfg)
        assert rt.field12 == {"key": "value", "n": 42}

    def test_static_field_not_in_roundtrip(self):
        # Static fields are included in to_dict output but ignored on load.
        d = BaseConfig().to_dict()
        assert "seed" in d
        # Loading with a different value for seed should have no effect.
        d["seed"] = 9999
        cfg = BaseConfig.from_dict(d)
        assert cfg.seed == 42  # always the class-level default


class TestDictRoundTripStrict:
    def test_strict_rejects_unknown_key(self):
        with pytest.raises(KeyError):
            BaseConfig.from_dict({"field1": "x", "unknown": 1}, strict=True)

    def test_nonstrict_ignores_unknown_key(self):
        cfg = BaseConfig.from_dict({"field1": "hi", "unknown": 1}, strict=False)
        assert cfg.field1 == "hi"


# ---------------------------------------------------------------------------
# Inherited config round-trip
# ---------------------------------------------------------------------------

class TestDictRoundTripInheritance:
    def test_child_config_round_trips(self):
        cfg = ChildConfig()
        cfg.field1 = "inherited"
        cfg.field17 = "extra"
        assert roundtrip_dict(ChildConfig, cfg) == cfg

    def test_grandchild_config_round_trips(self):
        cfg = GrandchildConfig()
        cfg.field1 = "overridden_value"
        assert roundtrip_dict(GrandchildConfig, cfg) == cfg


# ---------------------------------------------------------------------------
# Compound (unroll) config round-trip
# ---------------------------------------------------------------------------

class TestDictRoundTripCompound:
    def test_compound_round_trips(self):
        cfg = CompoundConfig()
        cfg.field1 = 7
        cfg.field18 = 2.71
        assert roundtrip_dict(CompoundConfig, cfg) == cfg

    def test_compound_to_dict_has_all_fields(self):
        d = CompoundConfig().to_dict()
        assert "field1" in d    # from IndependentConfig (wins on conflict)
        assert "field17" in d   # from GrandchildConfig
        assert "field18" in d   # from IndependentConfig only


# ---------------------------------------------------------------------------
# Nested config round-trip
# ---------------------------------------------------------------------------

class TestDictRoundTripNested:
    def test_nested_to_dict_structure(self):
        d = NestedConfig().to_dict()
        assert "independent" in d
        assert "grandchild" in d
        assert isinstance(d["independent"], dict)
        assert isinstance(d["grandchild"], dict)

    def test_nested_to_dict_values(self):
        n = NestedConfig()
        n.independent.field1 = 7
        d = n.to_dict()
        assert d["independent"]["field1"] == 7
        assert d["grandchild"]["field1"] == "overridden"  # default

    def test_nested_round_trip_defaults(self):
        n = NestedConfig()
        rt = NestedConfig.from_dict(n.to_dict())
        assert rt.independent.field1 == n.independent.field1
        assert rt.grandchild.field1 == n.grandchild.field1

    def test_nested_round_trip_modified(self):
        n = NestedConfig()
        n.independent.field1 = 42
        n.grandchild.field1 = "loaded"
        rt = NestedConfig.from_dict(n.to_dict())
        assert rt.independent.field1 == 42
        assert rt.grandchild.field1 == "loaded"

    def test_nested_instances_independent_after_roundtrip(self):
        n1 = NestedConfig.from_dict(NestedConfig().to_dict())
        n2 = NestedConfig.from_dict(NestedConfig().to_dict())
        n1.independent.field1 = 55
        assert n2.independent.field1 == 99


# ---------------------------------------------------------------------------
# Callable-default warning on serialization
# ---------------------------------------------------------------------------

class TestCallableDefaultWarning:
    def test_to_dict_warns_for_callable_default(self):
        class DerivedConfig(Config):
            base   = Float(2.0, "A base value")
            triple = Float(lambda self: self.base * 3, "3× base, unless overridden")

        cfg = DerivedConfig()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            d = cfg.to_dict()
        assert any("triple" in str(w.message) for w in caught)
        assert d["triple"] == 6.0  # snapshot of computed value

    def test_to_dict_no_warning_when_explicitly_set(self):
        class DerivedConfig(Config):
            base   = Float(2.0, "A base value")
            triple = Float(lambda self: self.base * 3, "3× base, unless overridden")

        cfg = DerivedConfig()
        cfg.triple = 99.0
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cfg.to_dict()
        assert not any("triple" in str(w.message) for w in caught)


# ---------------------------------------------------------------------------
# YAML round-trips
# ---------------------------------------------------------------------------

class TestYamlRoundTrip:
    def test_base_config_yaml(self):
        cfg = BaseConfig()
        cfg.field1 = "yaml_test"
        cfg.field2 = 3.14
        assert roundtrip_yaml(BaseConfig, cfg) == cfg

    def test_path_yaml(self):
        pytest.importorskip("yaml")
        cfg = ExtrasConfig()
        cfg.field8 = "/tmp/output"
        rt = roundtrip_yaml(ExtrasConfig, cfg)
        assert rt.field8 == pathlib.Path("/tmp/output")

    def test_range_yaml(self):
        pytest.importorskip("yaml")
        cfg = ExtrasConfig()
        cfg.field10 = (1.0, 5.0)
        rt = roundtrip_yaml(ExtrasConfig, cfg)
        assert rt.field10 == (1.0, 5.0)
        assert isinstance(rt.field10, tuple)

    def test_multioptions_yaml(self):
        pytest.importorskip("yaml")
        cfg = ExtrasConfig()
        cfg.field7 = {"b", "d"}
        rt = roundtrip_yaml(ExtrasConfig, cfg)
        assert rt.field7 == {"b", "d"}
        assert isinstance(rt.field7, set)

    def test_nested_yaml(self):
        pytest.importorskip("yaml")
        n = NestedConfig()
        n.independent.field1 = 77
        rt = roundtrip_yaml(NestedConfig, n)
        assert rt.independent.field1 == 77


# ---------------------------------------------------------------------------
# TOML round-trips
# ---------------------------------------------------------------------------

class TestTomlRoundTrip:
    def test_base_config_toml(self):
        cfg = BaseConfig()
        cfg.field1 = "toml_test"
        cfg.field2 = 2.71
        assert roundtrip_toml(BaseConfig, cfg) == cfg

    def test_path_toml(self):
        pytest.importorskip("tomli_w")
        cfg = ExtrasConfig()
        cfg.field8 = "/tmp/output"
        rt = roundtrip_toml(ExtrasConfig, cfg)
        assert rt.field8 == pathlib.Path("/tmp/output")

    def test_range_toml(self):
        pytest.importorskip("tomli_w")
        cfg = ExtrasConfig()
        cfg.field10 = (0.1, 0.9)
        rt = roundtrip_toml(ExtrasConfig, cfg)
        assert rt.field10 == (0.1, 0.9)
        assert isinstance(rt.field10, tuple)

    def test_multioptions_toml(self):
        pytest.importorskip("tomli_w")
        cfg = ExtrasConfig()
        cfg.field7 = {"a"}
        rt = roundtrip_toml(ExtrasConfig, cfg)
        assert rt.field7 == {"a"}
        assert isinstance(rt.field7, set)

    def test_nested_toml(self):
        pytest.importorskip("tomli_w")
        n = NestedConfig()
        n.grandchild.field1 = "toml_loaded"
        rt = roundtrip_toml(NestedConfig, n)
        assert rt.grandchild.field1 == "toml_loaded"
