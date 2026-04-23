"""Round-trip serialization tests for all composition modes and field types."""

import datetime
import pathlib

import pytest

from cfx import Config, Float

from .conftest import (
    BaseConfig,
    ChildConfig,
    DeepOuterConfig,
    ExtrasConfig,
    GrandchildConfig,
    MixedConfig,
    NestedConfig,
)

#############################################################################
# Helpers
#############################################################################


def roundtrip_dict(cls, instance):
    """Serialize instance to dict and reconstruct."""
    return cls.from_dict(instance.to_dict())


def roundtrip_yaml(cls, instance):
    pytest.importorskip("yaml", reason="pyyaml not installed")
    return cls.from_yaml(instance.to_yaml())


#############################################################################
# Flat config - dict round-trip, every field type
#############################################################################


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
        cfg = BaseConfig.from_dict(
            {"field1": "hi", "unknown": 1}, strict=False
        )
        assert cfg.field1 == "hi"


#############################################################################
# Inherited config round-trip
#############################################################################


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


#############################################################################
# Nested config round-trip
#############################################################################


class TestDictRoundTripNested:
    def test_nested_to_dict_structure(self):
        d = NestedConfig().to_dict()
        assert "independent" in d
        assert "grandchild" in d
        assert isinstance(d["independent"], dict)
        assert isinstance(d["grandchild"], dict)

    def test_nested_to_dict_values(self):
        n = NestedConfig()
        n.independent.int_field = 7
        d = n.to_dict()
        assert d["independent"]["int_field"] == 7
        assert d["grandchild"]["field1"] == "overridden"  # default

    def test_nested_round_trip_defaults(self):
        n = NestedConfig()
        rt = NestedConfig.from_dict(n.to_dict())
        assert rt.independent.int_field == n.independent.int_field
        assert rt.grandchild.field1 == n.grandchild.field1

    def test_nested_round_trip_modified(self):
        n = NestedConfig()
        n.independent.int_field = 42
        n.grandchild.field1 = "loaded"
        rt = NestedConfig.from_dict(n.to_dict())
        assert rt.independent.int_field == 42
        assert rt.grandchild.field1 == "loaded"

    def test_nested_instances_independent_after_roundtrip(self):
        n1 = NestedConfig.from_dict(NestedConfig().to_dict())
        n2 = NestedConfig.from_dict(NestedConfig().to_dict())
        n1.independent.int_field = 55
        assert n2.independent.int_field == 99


#############################################################################
# Callable-default warning on serialization
#############################################################################


class TestCallableDefaultSerialization:
    def test_callable_default_omitted_from_to_dict(self):
        class DerivedConfig(Config):
            base = Float(2.0, "A base value")
            triple = Float(
                lambda self: self.base * 3, "3x base, unless overridden"
            )

        d = DerivedConfig().to_dict()
        assert "triple" not in d
        assert d["base"] == 2.0

    def test_callable_with_stored_value_included(self):
        class DerivedConfig(Config):
            base = Float(2.0, "A base value")
            triple = Float(
                lambda self: self.base * 3, "3x base, unless overridden"
            )

        cfg = DerivedConfig()
        cfg.triple = 99.0
        assert cfg.to_dict()["triple"] == 99.0

    def test_transient_false_serializes_snapshot(self):
        class DerivedConfig(Config):
            base = Float(2.0, "A base value")
            triple = Float(
                lambda self: self.base * 3, "3x base", transient=False
            )

        d = DerivedConfig().to_dict()
        assert d["triple"] == 6.0


#############################################################################
# YAML round-trips
#############################################################################


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
        n.independent.int_field = 77
        rt = roundtrip_yaml(NestedConfig, n)
        assert rt.independent.int_field == 77


#############################################################################
# TOML round-trips
#############################################################################


#############################################################################
# Multi-level nested config round-trips
#############################################################################


class TestDeepNestedRoundTrip:
    def test_yaml(self):
        pytest.importorskip("yaml")
        cfg = DeepOuterConfig()
        cfg.middle.inner.x = 9.9
        rt = roundtrip_yaml(DeepOuterConfig, cfg)
        assert rt.middle.inner.x == 9.9

    def test_middle_own_field_yaml(self):
        pytest.importorskip("yaml")
        cfg = DeepOuterConfig()
        cfg.middle.y = 7.7
        cfg.middle.inner.x = 3.3
        rt = roundtrip_yaml(DeepOuterConfig, cfg)
        assert rt.middle.y == 7.7
        assert rt.middle.inner.x == 3.3


#############################################################################
# Mixed flat+nested round-trips
#############################################################################


class TestMixedConfigRoundTrip:
    def test_dict_round_trip(self):
        cfg = MixedConfig()
        cfg.top_field = 42.0
        cfg.inner.x = 5.5
        rt = roundtrip_dict(MixedConfig, cfg)
        assert rt.top_field == 42.0
        assert rt.inner.x == 5.5

    def test_to_dict_structure(self):
        d = MixedConfig().to_dict()
        assert d["top_field"] == 99.0
        assert d["inner"]["x"] == 1.0

    def test_yaml_round_trip(self):
        pytest.importorskip("yaml")
        cfg = MixedConfig()
        cfg.top_field = 42.0
        cfg.inner.x = 5.5
        rt = roundtrip_yaml(MixedConfig, cfg)
        assert rt.top_field == 42.0
        assert rt.inner.x == 5.5
