"""Tests for Config class methods, composition, and serialization."""

import pytest

from cfx import Config, Float, FrozenConfigError, Int, String

from .conftest import (
    BaseConfig,
    ChildConfig,
    CompoundConfig,
    DeepOuterConfig,
    GrandchildConfig,
    MixedConfig,
    NestedConfig,
)

#############################################################################
# confid auto-naming
#############################################################################


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


#############################################################################
# Basic Config methods
#############################################################################


class TestConfigMethods:
    def test_keys(self, base):
        assert set(base.keys()) == {
            "field1",
            "field2",
            "field3",
            "field4",
            "field5",
            "field6",
            "seed",
        }

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


#############################################################################
# copy and diff
#############################################################################


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


#############################################################################
# update
#############################################################################


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


#############################################################################
# freeze
#############################################################################


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


#############################################################################
# validate
#############################################################################


class TestValidate:
    def test_base_validate_is_noop(self, base):
        base.validate()  # should not raise

    def test_custom_validate_called_on_from_dict(self):
        class C(Config):
            field1 = Int(5, "value a")
            field2 = Int(10, "value b, must be > field1")

            def validate(self):
                if self.field2 <= self.field1:
                    raise ValueError("field2 must be > field1")

        with pytest.raises(ValueError):
            C.from_dict({"field1": 10, "field2": 5})

    def test_custom_validate_passes_when_valid(self):
        class C(Config):
            field1 = Int(5, "value a")
            field2 = Int(10, "value b")

            def validate(self):
                if self.field2 <= self.field1:
                    raise ValueError

        c = C.from_dict({"field1": 3, "field2": 7})
        assert c.field1 == 3


#############################################################################
# to_dict / from_dict
#############################################################################


class TestSerialization:
    def test_to_dict_contains_all_fields(self, base):
        d = base.to_dict()
        for k in base:
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


#############################################################################
# Inheritance
#############################################################################


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
        for f in (
            "field1",
            "field2",
            "field3",
            "field4",
            "field5",
            "field6",
            "field17",
        ):
            assert f in g

    def test_parent_unaffected_by_child_override(self):
        assert BaseConfig().field1 == "a"


#############################################################################
# Compound composition (unroll)
#############################################################################


class TestCompoundComposition:
    def test_compound_has_fields_from_all_components(self):
        c = CompoundConfig()
        assert "int_field" in c  # from IndependentConfig
        assert "field17" in c  # from GrandchildConfig
        assert "field18" in c  # from IndependentConfig only

    def test_compound_instances_are_independent(self):
        c1 = CompoundConfig()
        c2 = CompoundConfig()
        c1.field18 = 0.0
        assert c2.field18 == 3.14

    def test_compound_str_includes_all_fields(self):
        s = str(CompoundConfig())
        assert "int_field" in s
        assert "field18" in s

    def test_compound_to_dict(self):
        d = CompoundConfig().to_dict()
        assert "int_field" in d
        assert "field18" in d

    def test_duplicate_fields_raise(self):
        class A(Config):
            confid = "a"
            x = String("a", "doc")

        class B(Config):
            confid = "b"
            x = String("b", "doc")

        with pytest.raises(ValueError, match="Duplicate fields"):

            class Bad(Config, components=[A, B], method="unroll"):
                pass


#############################################################################
# Nested composition
#############################################################################


class TestNestedComposition:
    def test_nested_sub_configs_accessible_by_confid(self):
        n = NestedConfig()
        assert hasattr(n, "independent")
        assert hasattr(n, "grandchild")

    def test_nested_sub_config_field_access(self):
        n = NestedConfig()
        assert n.independent.int_field == 99
        assert n.grandchild.field1 == "overridden"

    def test_nested_sub_configs_settable(self):
        n = NestedConfig()
        n.independent.int_field = 7
        assert n.independent.int_field == 7

    def test_nested_sub_configs_printable(self):
        n = NestedConfig()
        # sub-configs are full Config instances - they should print fine
        s = str(n.independent)
        assert "int_field" in s

    def test_nested_instances_are_independent(self):
        n1 = NestedConfig()
        n2 = NestedConfig()
        n1.independent.int_field = 7
        assert n2.independent.int_field == 99  # should be unaffected

    def test_nested_str_shows_sub_config_summary(self):
        s = str(NestedConfig())
        assert "IndependentConfig" in s

    def test_nested_str_has_box_drawing(self):
        s = str(NestedConfig())
        assert "├─" in s or "└─" in s


#############################################################################
# Multi-level nested composition
#############################################################################


class TestDeepNested:
    def test_construction(self):
        cfg = DeepOuterConfig()
        assert cfg.middle.inner.x == 1.0

    def test_assignment(self):
        cfg = DeepOuterConfig()
        cfg.middle.inner.x = 9.9
        assert cfg.middle.inner.x == 9.9

    def test_instances_are_independent(self):
        c1 = DeepOuterConfig()
        c2 = DeepOuterConfig()
        c1.middle.inner.x = 9.9
        assert c2.middle.inner.x == 1.0

    def test_to_dict_structure(self):
        d = DeepOuterConfig().to_dict()
        assert "middle" in d
        assert "inner" in d["middle"]
        assert d["middle"]["inner"]["x"] == 1.0

    def test_from_dict_round_trip(self):
        cfg = DeepOuterConfig()
        cfg.middle.inner.x = 9.9
        rt = DeepOuterConfig.from_dict(cfg.to_dict())
        assert rt.middle.inner.x == 9.9

    def test_str(self):
        s = str(DeepOuterConfig())
        assert "middle" in s

    def test_str_has_box_drawing(self):
        s = str(DeepOuterConfig())
        assert "└─" in s

    def test_middle_has_own_field(self):
        cfg = DeepOuterConfig()
        assert cfg.middle.y == 2.0

    def test_middle_to_dict_includes_own_field(self):
        d = DeepOuterConfig().to_dict()
        assert d["middle"]["y"] == 2.0
        assert d["middle"]["inner"]["x"] == 1.0

    def test_middle_from_dict_round_trip(self):
        cfg = DeepOuterConfig()
        cfg.middle.y = 7.7
        cfg.middle.inner.x = 9.9
        rt = DeepOuterConfig.from_dict(cfg.to_dict())
        assert rt.middle.y == 7.7
        assert rt.middle.inner.x == 9.9


#############################################################################
# Mixed flat+nested composition
#############################################################################


class TestMixedConfig:
    def test_flat_field_accessible(self):
        cfg = MixedConfig()
        assert cfg.top_field == 99.0

    def test_sub_config_accessible(self):
        cfg = MixedConfig()
        assert cfg.inner.x == 1.0

    def test_contains_flat_key(self):
        cfg = MixedConfig()
        assert "top_field" in cfg

    def test_contains_confid(self):
        cfg = MixedConfig()
        assert "inner" in cfg

    def test_to_dict_structure(self):
        d = MixedConfig().to_dict()
        assert d["top_field"] == 99.0
        assert d["inner"]["x"] == 1.0

    def test_from_dict_round_trip(self):
        cfg = MixedConfig()
        cfg.top_field = 42.0
        cfg.inner.x = 5.5
        rt = MixedConfig.from_dict(cfg.to_dict())
        assert rt.top_field == 42.0
        assert rt.inner.x == 5.5

    def test_eq_equal_instances(self):
        assert MixedConfig() == MixedConfig()

    def test_eq_different_flat_field(self):
        a = MixedConfig()
        b = MixedConfig()
        b.top_field = 1.0
        assert a != b

    def test_eq_different_sub_config(self):
        a = MixedConfig()
        b = MixedConfig()
        b.inner.x = 9.9
        assert a != b

    def test_copy_preserves_flat_and_sub(self):
        cfg = MixedConfig()
        cfg.top_field = 3.0
        cfg.inner.x = 7.0
        c = cfg.copy()
        assert c.top_field == 3.0
        assert c.inner.x == 7.0

    def test_copy_is_independent(self):
        cfg = MixedConfig()
        c = cfg.copy()
        c.top_field = 1.0
        c.inner.x = 1.0
        assert cfg.top_field == 99.0
        assert cfg.inner.x == 1.0

    def test_str_has_flat_field_and_sub_section(self):
        s = str(MixedConfig())
        assert "top_field" in s
        assert "inner" in s

    def test_instances_are_independent(self):
        c1 = MixedConfig()
        c2 = MixedConfig()
        c1.top_field = 0.0
        c1.inner.x = 0.0
        assert c2.top_field == 99.0
        assert c2.inner.x == 1.0


#############################################################################
# __getitem__ for nested configs
#############################################################################


class TestGetItemNested:
    def test_getitem_returns_nested_sub_config(self):
        cfg = NestedConfig()
        sub = cfg["independent"]
        assert sub is cfg.independent

    def test_getitem_raises_for_unknown_key(self):
        cfg = NestedConfig()
        with pytest.raises(KeyError):
            cfg["no_such_key"]

    def test_contains_and_getitem_consistent(self):
        cfg = NestedConfig()
        for key in ("independent", "grandchild"):
            assert key in cfg
            assert cfg[key] is getattr(cfg, key)


#############################################################################
# Duplicate confid detection
#############################################################################


class TestDuplicateConfid:
    def test_duplicate_confid_raises(self):
        class A(Config):
            confid = "shared"
            x = Float(1.0, "x")

        class B(Config):
            confid = "shared"
            y = Float(2.0, "y")

        with pytest.raises(ValueError, match="shared"):

            class Bad(Config, components=[A, B]):
                pass


#############################################################################
# Environment variable field precedence
#############################################################################


class TestEnvVarPrecedence:
    def test_env_var_used_when_no_explicit_value(self, monkeypatch):
        monkeypatch.setenv("CFX_TEST_HOST", "env.example.com")

        class C(Config):
            host = String("default", "host", env="CFX_TEST_HOST")

        assert C().host == "env.example.com"

    def test_explicit_value_beats_env_var(self, monkeypatch):
        monkeypatch.setenv("CFX_TEST_HOST", "env.example.com")

        class C(Config):
            host = String("default", "host", env="CFX_TEST_HOST")

        c = C()
        c.host = "explicit.example.com"
        assert c.host == "explicit.example.com"

    def test_default_used_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("CFX_TEST_HOST", raising=False)

        class C(Config):
            host = String("default.example.com", "host", env="CFX_TEST_HOST")

        assert C().host == "default.example.com"


#############################################################################
# HTML representation
#############################################################################


class TestReprHtml:
    def test_repr_html_returns_string(self):
        html = NestedConfig()._repr_html_()
        assert isinstance(html, str)

    def test_repr_html_starts_with_pre(self):
        html = NestedConfig()._repr_html_()
        assert html.startswith("<pre>")

    def test_repr_html_contains_table(self):
        html = NestedConfig()._repr_html_()
        assert "<table>" in html
