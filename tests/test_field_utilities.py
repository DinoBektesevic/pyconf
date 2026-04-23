"""Tests for is_set(), unset(), and reset() on ConfigField."""

import pytest

from cfx import Config, Float, Int, Path, String

#############################################################################
# is_set
#############################################################################


class TestIsSet:
    def test_regular_field_is_set_after_init(self):
        # Config.__init__ pre-populates non-callable defaults into __dict__
        # so every instance starts with explicit storage for regular fields.
        class C(Config):
            x = Float(1.0, "doc")

        c = C()
        descriptor = type(c)._fields["x"]
        assert descriptor.is_set(c)

    def test_callable_default_not_set_before_assignment(self):
        # Callable-default fields are left unset so __get__ can evaluate them
        # lazily. is_set() is the public way to detect this state.
        class C(Config):
            base = Float(2.0, "doc")
            derived = Float(lambda self: self.base * 3, "doc")

        c = C()
        descriptor = type(c)._fields["derived"]
        assert not descriptor.is_set(c)

    def test_callable_default_set_after_explicit(self):
        class C(Config):
            base = Float(2.0, "doc")
            derived = Float(lambda self: self.base * 3, "doc")

        c = C()
        c.derived = 99.0
        descriptor = type(c)._fields["derived"]
        assert descriptor.is_set(c)

    def test_static_field_not_set(self):
        class C(Config):
            x = Int(42, "doc", static=True)

        c = C()
        descriptor = type(c)._fields["x"]
        # static fields have no per-instance storage
        assert not descriptor.is_set(c)

    def test_false_after_unset(self):
        class C(Config):
            x = Float(1.0, "doc")

        c = C()
        descriptor = type(c)._fields["x"]
        assert descriptor.is_set(c)  # pre-populated
        descriptor.unset(c)
        assert not descriptor.is_set(c)

    def test_independent_instances_callable(self):
        class C(Config):
            derived = Float(lambda self: 0.0, "doc")

        c1, c2 = C(), C()
        c1.derived = 5.0
        descriptor = type(c1)._fields["derived"]
        assert descriptor.is_set(c1)
        assert not descriptor.is_set(c2)


#############################################################################
# unset
#############################################################################


class TestUnset:
    def test_reverts_to_default(self):
        class C(Config):
            x = Float(1.0, "doc")

        c = C()
        c.x = 99.0
        descriptor = type(c)._fields["x"]
        descriptor.unset(c)
        assert c.x == 1.0
        assert not descriptor.is_set(c)

    def test_unset_on_unset_field_is_noop(self):
        class C(Config):
            x = Float(1.0, "doc")

        c = C()
        descriptor = type(c)._fields["x"]
        descriptor.unset(c)  # should not raise
        assert c.x == 1.0

    def test_unset_restores_callable_default(self):
        class C(Config):
            base = Float(2.0, "doc")
            derived = Float(lambda self: self.base * 3, "doc")

        c = C()
        c.derived = 0.0
        descriptor = type(c)._fields["derived"]
        descriptor.unset(c)
        assert c.derived == 6.0  # recomputed from base

    def test_unset_does_not_affect_other_instances(self):
        class C(Config):
            x = Float(1.0, "doc")

        c1, c2 = C(), C()
        c1.x = 5.0
        c2.x = 7.0
        descriptor = type(c1)._fields["x"]
        descriptor.unset(c1)
        assert c1.x == 1.0
        assert c2.x == 7.0


#############################################################################
# reset
#############################################################################


class TestReset:
    def test_reset_none_equivalent_to_unset(self):
        class C(Config):
            x = Float(1.0, "doc")

        c = C()
        c.x = 5.0
        descriptor = type(c)._fields["x"]
        descriptor.reset(c)
        assert c.x == 1.0
        assert not descriptor.is_set(c)

    def test_reset_with_value_sets_and_validates(self):
        class C(Config):
            x = Float(1.0, "doc", maxval=10.0)

        c = C()
        descriptor = type(c)._fields["x"]
        descriptor.reset(c, 7.0)
        assert c.x == 7.0
        assert descriptor.is_set(c)

    def test_reset_with_value_rejects_invalid(self):
        class C(Config):
            x = Float(1.0, "doc", maxval=10.0)

        c = C()
        descriptor = type(c)._fields["x"]
        with pytest.raises(ValueError):
            descriptor.reset(c, 99.0)

    def test_reset_with_value_runs_normalize(self):
        class C(Config):
            p = Path("./out", "doc")

        c = C()
        descriptor = type(c)._fields["p"]
        descriptor.reset(c, "/tmp/data")
        import pathlib

        assert c.p == pathlib.Path("/tmp/data")

    def test_reset_replaces_previous_value(self):
        class C(Config):
            x = Float(1.0, "doc")

        c = C()
        c.x = 5.0
        descriptor = type(c)._fields["x"]
        descriptor.reset(c, 3.0)
        assert c.x == 3.0


#############################################################################
# Round-trip: set -> is_set -> unset -> is_set
#############################################################################


class TestIsSetUnsetRoundTrip:
    def test_round_trip(self):
        # Regular fields start as set (pre-populated by __init__). unset()
        # removes the stored value and reverts to the default.
        class C(Config):
            label = String("default", "doc")

        c = C()
        d = type(c)._fields["label"]

        assert d.is_set(c)  # pre-populated
        c.label = "hello"
        assert d.is_set(c)
        assert c.label == "hello"
        d.unset(c)
        assert not d.is_set(c)
        assert c.label == "default"
