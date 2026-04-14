"""Tests for Config class methods, composition, and serialization."""

import pytest

from pyconf import Config, ConfigField, FrozenConfigError, Int, Float, String, Options
from .conftest import (
    BaseConfig, ExtrasConfig, ChildConfig, GrandchildConfig,
    IndependentConfig, CompoundConfig, NestedConfig,
)


# ---------------------------------------------------------------------------
# confid auto-naming
# ---------------------------------------------------------------------------

class TestConfid:
    def test_explicit_confid(self):
        assert BaseConfig.confid == "base"

    def test_auto_confid_is_lowercase_classname(self):
        class MySpecialConfig(Config):
            f = Int(1, "doc")
        assert MySpecialConfig.confid == "myspecialconfig"

    def test_auto_confid_not_inherited(self):
        # Each class in the hierarchy gets its own confid
        assert ChildConfig.confid == "child"
        assert GrandchildConfig.confid == "grandchild"


# ---------------------------------------------------------------------------
# Basic Config methods
# ---------------------------------------------------------------------------

class TestConfigMethods:
    def test_keys(self, base):
        assert set(base.keys()) == {"field1", "field2", "field3", "field4", "field5", "field6", "seed"}

    def test_values_returns_defaults(self, base):
        assert base.field1 == "a"
        assert base.field2 == 1.0

    def test_items(self, base):
        d = dict(base.items())
        assert d["field1"] == "a"
        assert d["field3"] == 10

    def test_getitem(self, base):
        assert base["field1"] == "a"

    def test_setitem(self, base):
        base["field1"] = "z"
        assert base.field1 == "z"

    def test_setitem_validates(self, base):
        with pytest.raises(TypeError):
            base["field1"] = 99  # String field

    def test_setitem_unknown_key_raises(self, base):
        with pytest.raises(KeyError):
            base["no_such_field"] = 1

    def test_contains_known_field(self, base):
        assert "field1" in base

    def test_contains_unknown_field(self, base):
        assert "no_such_field" not in base

    def test_eq_equal_instances(self):
        assert BaseConfig() == BaseConfig()

    def test_eq_different_values(self, base):
        other = BaseConfig()
        other.field1 = "different"
        assert base != other

    def test_eq_different_types(self, base, extras):
        assert base != extras

    def test_repr(self, base):
        r = repr(base)
        assert r.startswith("BaseConfig(")
        assert "field1=" in r

    def test_str_contains_field_names(self, base):
        s = str(base)
        assert "field1" in s
        assert "field2" in s

    def test_str_contains_doc(self, base):
        s = str(base)
        assert "A string field" in s


# ---------------------------------------------------------------------------
# copy and diff
# ---------------------------------------------------------------------------

class TestCopyDiff:
    def test_copy_is_equal(self, base):
        assert base.copy() == base

    def test_copy_is_independent(self, base):
        c = base.copy()
        c.field1 = "modified"
        assert base.field1 == "a"

    def test_copy_with_overrides(self, base):
        c = base.copy(field1="new", field2=9.9)
        assert c.field1 == "new"
        assert c.field2 == 9.9
        assert c.field3 == base.field3  # unchanged

    def test_copy_validates_overrides(self, base):
        with pytest.raises(TypeError):
            base.copy(field1=99)  # String field

    def test_diff_empty_for_equal(self, base):
        assert base.diff(base.copy()) == {}

    def test_diff_shows_changed_fields(self, base):
        other = base.copy(field1="different", field2=99.0)
        d = base.diff(other)
        assert "field1" in d
        assert "field2" in d
        assert "field3" not in d

    def test_diff_wrong_type_raises(self, base, extras):
        with pytest.raises(TypeError):
            base.diff(extras)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_sets_multiple_fields(self, base):
        base.update({"field1": "updated", "field2": 5.0})
        assert base.field1 == "updated"
        assert base.field2 == 5.0

    def test_update_validates(self, base):
        with pytest.raises(TypeError):
            base.update({"field1": 99})

    def test_update_unknown_key_raises(self, base):
        with pytest.raises(KeyError):
            base.update({"no_such_field": 1})


# ---------------------------------------------------------------------------
# freeze
# ---------------------------------------------------------------------------

class TestFreeze:
    def test_freeze_prevents_set(self, base):
        base.freeze()
        with pytest.raises(FrozenConfigError):
            base.field1 = "nope"

    def test_freeze_prevents_setitem(self, base):
        base.freeze()
        with pytest.raises(FrozenConfigError):
            base["field1"] = "nope"

    def test_field_value_unchanged_after_freeze(self, base):
        base.field1 = "before"
        base.freeze()
        with pytest.raises(FrozenConfigError):
            base.field1 = "after"
        assert base.field1 == "before"


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_base_validate_is_noop(self, base):
        base.validate()  # should not raise

    def test_custom_validate_called_on_from_dict(self):
        class C(Config):
            field1 = Int(5,  "value a")
            field2 = Int(10, "value b, must be > field1")

            def validate(self):
                if self.field2 <= self.field1:
                    raise ValueError("field2 must be > field1")

        with pytest.raises(ValueError):
            C.from_dict({"field1": 10, "field2": 5})

    def test_custom_validate_passes_when_valid(self):
        class C(Config):
            field1 = Int(5,  "value a")
            field2 = Int(10, "value b")

            def validate(self):
                if self.field2 <= self.field1:
                    raise ValueError

        c = C.from_dict({"field1": 3, "field2": 7})
        assert c.field1 == 3


# ---------------------------------------------------------------------------
# to_dict / from_dict
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_to_dict_contains_all_fields(self, base):
        d = base.to_dict()
        for k in base.keys():
            assert k in d

    def test_to_dict_values_match(self, base):
        d = base.to_dict()
        assert d["field1"] == base.field1
        assert d["field2"] == base.field2

    def test_from_dict_round_trip(self, base):
        base.field1 = "round_trip"
        base.field2 = 7.7
        assert BaseConfig.from_dict(base.to_dict()) == base

    def test_from_dict_strict_rejects_unknown_key(self):
        with pytest.raises(KeyError):
            BaseConfig.from_dict({"field1": "x", "unknown": 99}, strict=True)

    def test_from_dict_nonstrict_ignores_unknown_key(self):
        c = BaseConfig.from_dict({"field1": "x", "unknown": 99}, strict=False)
        assert c.field1 == "x"

    def test_from_dict_validates_values(self):
        with pytest.raises(TypeError):
            BaseConfig.from_dict({"field1": 99})  # String field, got int


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------

class TestInheritance:
    def test_child_has_parent_fields(self):
        c = ChildConfig()
        assert "field1" in c
        assert "field17" in c

    def test_grandchild_overrides_field1(self):
        g = GrandchildConfig()
        assert g.field1 == "overridden"

    def test_grandchild_has_all_ancestor_fields(self):
        g = GrandchildConfig()
        for f in ("field1", "field2", "field3", "field4", "field5", "field6", "field17"):
            assert f in g

    def test_parent_unaffected_by_child_override(self):
        assert BaseConfig().field1 == "a"


# ---------------------------------------------------------------------------
# Compound composition (unroll)
# ---------------------------------------------------------------------------

class TestCompoundComposition:
    def test_compound_has_fields_from_all_components(self):
        c = CompoundConfig()
        assert "field1" in c   # from both; IndependentConfig wins (first in list)
        assert "field17" in c  # from GrandchildConfig
        assert "field18" in c  # from IndependentConfig only

    def test_compound_field1_is_int_from_independent(self):
        # IndependentConfig.field1 is Int(99); GrandchildConfig.field1 is String
        # IndependentConfig is listed first so its field1 should win
        c = CompoundConfig()
        assert isinstance(c.field1, int)
        assert c.field1 == 99

    def test_compound_instances_are_independent(self):
        c1 = CompoundConfig()
        c2 = CompoundConfig()
        c1.field18 = 0.0
        assert c2.field18 == 3.14

    def test_compound_str_includes_all_fields(self):
        s = str(CompoundConfig())
        assert "field1" in s
        assert "field18" in s

    def test_compound_to_dict(self):
        d = CompoundConfig().to_dict()
        assert "field1" in d
        assert "field18" in d


# ---------------------------------------------------------------------------
# Nested composition
# ---------------------------------------------------------------------------

class TestNestedComposition:
    def test_nested_sub_configs_accessible_by_confid(self):
        n = NestedConfig()
        assert hasattr(n, "independent")
        assert hasattr(n, "grandchild")

    def test_nested_sub_config_field_access(self):
        n = NestedConfig()
        assert n.independent.field1 == 99
        assert n.grandchild.field1 == "overridden"

    def test_nested_sub_configs_settable(self):
        n = NestedConfig()
        n.independent.field1 = 7
        assert n.independent.field1 == 7

    def test_nested_sub_configs_printable(self):
        n = NestedConfig()
        # sub-configs are full Config instances — they should print fine
        s = str(n.independent)
        assert "field1" in s

    def test_nested_instances_are_independent(self):
        n1 = NestedConfig()
        n2 = NestedConfig()
        n1.independent.field1 = 7
        assert n2.independent.field1 == 99  # should be unaffected

    def test_nested_str_shows_sub_config_summary(self):
        s = str(NestedConfig())
        assert "independent" in s
