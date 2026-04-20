"""Tests for Alias, ConfigView, Mirror, AliasedView, and FlatView."""

import pytest

from cfx import (
    Alias,
    AliasedView,
    Config,
    ConfigView,
    FlatView,
    Float,
    Int,
    Mirror,
    String,
)

#############################################################################
# Shared test configs
#############################################################################


class InnerConfig(Config):
    confid = "inner"
    x = Float(1.0, "x value")
    y = Int(0, "y value")


class OuterConfig(Config, components=[InnerConfig]):
    confid = "outer"
    z = Float(9.0, "outer own field")


class SiblingConfig(Config):
    confid = "sibling"
    name = String("default", "a name")


class MultiConfig(Config, components=[InnerConfig, SiblingConfig]):
    confid = "multi"


#############################################################################
# Alias — basic descriptor behaviour
#############################################################################


class TestAlias:
    def test_alias_from_fieldref(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        assert V._aliases["x_val"]._path == "x"

    def test_alias_from_string(self):
        class V(ConfigView):
            x_val = Alias("x")

        assert V._aliases["x_val"]._path == "x"

    def test_alias_get(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        assert V(cfg).x_val == 1.0

    def test_alias_set_writes_through(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        v = V(cfg)
        v.x_val = 7.0
        assert cfg.x == 7.0

    def test_alias_dotpath_get(self):
        class V(ConfigView):
            x_val = Alias(OuterConfig.inner.x)

        cfg = OuterConfig()
        assert V(cfg).x_val == 1.0

    def test_alias_dotpath_set(self):
        class V(ConfigView):
            x_val = Alias(OuterConfig.inner.x)

        cfg = OuterConfig()
        V(cfg).x_val = 5.5
        assert cfg.inner.x == 5.5

    def test_alias_class_access_returns_fieldref(self):
        from cfx.refs import FieldRef

        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        assert isinstance(V.x_val, FieldRef)
        assert V.x_val._path == "x_val"

    def test_multiple_aliases(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)
            y_val = Alias(InnerConfig.y)

        cfg = InnerConfig()
        cfg.y = 42
        v = V(cfg)
        assert v.x_val == 1.0
        assert v.y_val == 42


#############################################################################
# ConfigView — binding and delegation
#############################################################################


class TestConfigView:
    def test_binds_to_config(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        v = V(cfg)
        assert v._alias_root is cfg

    def test_write_visible_on_config(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        V(cfg).x_val = 3.0
        assert cfg.x == 3.0

    def test_aliases_collected_on_subclass(self):
        class V(ConfigView):
            a = Alias(InnerConfig.x)
            b = Alias(InnerConfig.y)

        assert set(V._aliases) == {"a", "b"}

    def test_span_multiple_subconfigs(self):
        class V(ConfigView):
            x_val = Alias(MultiConfig.inner.x)
            label = Alias(MultiConfig.sibling.name)

        cfg = MultiConfig()
        cfg.inner.x = 2.5
        cfg.sibling.name = "hello"
        v = V(cfg)
        assert v.x_val == 2.5
        assert v.label == "hello"

    def test_view_does_not_copy_data(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        v = V(cfg)
        cfg.x = 99.0
        assert v.x_val == 99.0  # reflects live value, not a snapshot


#############################################################################
# ConfigView — to_dict / from_dict
#############################################################################


class TestConfigViewSerialization:
    def test_to_dict(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)
            y_val = Alias(InnerConfig.y)

        cfg = InnerConfig()
        cfg.x = 3.0
        cfg.y = 7
        assert V(cfg).to_dict() == {"x_val": 3.0, "y_val": 7}

    def test_from_dict_applies_values(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        V.from_dict({"x_val": 5.0}, cfg)
        assert cfg.x == 5.0

    def test_from_dict_ignores_unknown_keys(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        V.from_dict({"x_val": 2.0, "unknown": 99}, cfg)
        assert cfg.x == 2.0

    def test_from_dict_returns_bound_view(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        v = V.from_dict({"x_val": 4.0}, cfg)
        assert isinstance(v, V)
        assert v._alias_root is cfg


#############################################################################
# ConfigView — repr / _repr_html_
#############################################################################


class TestConfigViewDisplay:
    def test_repr_contains_class_name(self):
        class CalibView(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        assert "CalibView" in repr(CalibView(cfg))

    def test_repr_contains_value(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        cfg = InnerConfig()
        cfg.x = 7.7
        assert "7.7" in repr(V(cfg))

    def test_repr_html_contains_alias_and_path(self):
        class V(ConfigView):
            x_val = Alias(InnerConfig.x)

        html = V._repr_html_()
        assert "x_val" in html
        assert "x" in html


#############################################################################
# Mirror — descriptor on a Config
#############################################################################


class TwinConfig(Config):
    confid = "twin"
    x = Float(1.0, "x value")
    y = Int(0, "y value")


class MirroredConfig(Config, components=[InnerConfig, TwinConfig]):
    confid = "mirrored"
    shared_x = Mirror("inner.x", "twin.x")


class TestMirror:
    def test_mirror_write_fans_out(self):
        cfg = MirroredConfig()
        cfg.shared_x = 5.0
        assert cfg.inner.x == 5.0
        assert cfg.twin.x == 5.0

    def test_mirror_read_returns_shared_value(self):
        cfg = MirroredConfig()
        cfg.inner.x = 3.0
        cfg.twin.x = 3.0
        assert cfg.shared_x == 3.0

    def test_mirror_read_raises_on_disagreement(self):
        cfg = MirroredConfig()
        cfg.inner.x = 1.0
        cfg.twin.x = 2.0
        with pytest.raises(ValueError, match="disagree"):
            _ = cfg.shared_x

    def test_mirror_class_access_returns_fieldref(self):
        from cfx.refs import FieldRef

        assert isinstance(MirroredConfig.shared_x, FieldRef)
        assert MirroredConfig.shared_x._path == "shared_x"

    def test_mirror_fieldref_paths(self):
        # OuterConfig already has InnerConfig under confid "inner";
        # use it to get a FieldRef with the full relative path "inner.x".
        class FRefMirrorConfig(Config, components=[InnerConfig, TwinConfig]):
            confid = "fref_mirror"
            shared_x = Mirror(OuterConfig.inner.x, "twin.x")

        cfg = FRefMirrorConfig()
        cfg.shared_x = 7.0
        assert cfg.inner.x == 7.0
        assert cfg.twin.x == 7.0


#############################################################################
# AliasedView — auto-generated prefixed aliases
#############################################################################


class TestAliasedView:
    def test_default_prefix_is_confid(self):
        class V(AliasedView, components=[InnerConfig]):
            pass

        assert "inner_x" in V._aliases
        assert "inner_y" in V._aliases

    def test_custom_prefix(self):
        class V(AliasedView, components=[InnerConfig], aliases=["cam"]):
            pass

        assert "cam_x" in V._aliases
        assert "cam_y" in V._aliases

    def test_read_through_alias(self):
        class V(AliasedView, components=[InnerConfig]):
            pass

        v = V()
        assert v.inner_x == 1.0

    def test_write_through_alias(self):
        class V(AliasedView, components=[InnerConfig]):
            pass

        v = V()
        v.inner_x = 9.9
        assert v.inner.x == 9.9

    def test_init_takes_no_args(self):
        class V(AliasedView, components=[InnerConfig]):
            pass

        v = V()
        assert isinstance(v.inner, InnerConfig)

    def test_instances_are_independent(self):
        class V(AliasedView, components=[InnerConfig]):
            pass

        v1, v2 = V(), V()
        v1.inner_x = 5.0
        assert v2.inner_x == 1.0

    def test_multiple_components(self):
        class V(AliasedView, components=[InnerConfig, SiblingConfig]):
            pass

        v = V()
        v.inner_x = 2.5
        v.sibling_name = "hello"
        assert v.inner.x == 2.5
        assert v.sibling.name == "hello"

    def test_conflict_raises_at_class_definition(self):
        class Dup(Config):
            confid = "dup"
            x = Float(0.0, "x")

        with pytest.raises(ValueError, match="conflict"):

            class V(
                AliasedView, components=[InnerConfig, Dup], aliases=["p", "p"]
            ):
                pass

    def test_aliases_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="same length"):

            class V(
                AliasedView,
                components=[InnerConfig, SiblingConfig],
                aliases=["a"],
            ):
                pass

    def test_to_dict(self):
        class V(AliasedView, components=[InnerConfig]):
            pass

        v = V()
        v.inner_x = 3.0
        d = v.to_dict()
        assert d["inner_x"] == 3.0
        assert d["inner_y"] == 0

    def test_from_dict(self):
        class V(AliasedView, components=[InnerConfig]):
            pass

        v = V.from_dict({"inner_x": 7.0})
        assert isinstance(v, V)
        assert v.inner.x == 7.0

    def test_none_prefix_flat_names(self):
        class V(AliasedView, components=[InnerConfig], aliases=[None]):
            pass

        assert "x" in V._aliases
        assert "y" in V._aliases
        v = V()
        v.x = 4.0
        assert v.inner.x == 4.0

    def test_none_prefix_conflict_raises(self):
        class AlsoHasX(Config):
            confid = "alsox"
            x = Float(0.0, "x")

        with pytest.raises(ValueError, match="conflict"):

            class V(
                AliasedView,
                components=[InnerConfig, AlsoHasX],
                aliases=[None, None],
            ):
                pass


#############################################################################
# FlatView — unprefixed auto-aliases
#############################################################################


class TestFlatView:
    def test_flat_aliases_generated(self):
        class V(FlatView, components=[InnerConfig]):
            pass

        assert "x" in V._aliases
        assert "y" in V._aliases

    def test_flat_read_write(self):
        class V(FlatView, components=[InnerConfig]):
            pass

        v = V()
        v.x = 6.0
        assert v.inner.x == 6.0

    def test_flat_conflict_raises(self):
        class Clash(Config):
            confid = "clash"
            x = Float(0.0, "x")

        with pytest.raises(ValueError, match="conflict"):

            class V(FlatView, components=[InnerConfig, Clash]):
                pass
