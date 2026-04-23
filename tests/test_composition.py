"""Tests for Config composition via inheritance and components=."""

import pytest

from cfx import Config, Float, Int, String

#############################################################################
# Helpers
#############################################################################


class Inner(Config):
    confid = "inner"
    x = Float(1.0, "inner x")


class Middle(Config, components=[Inner]):
    confid = "middle"
    y = Float(2.0, "middle y")


class Outer(Config, components=[Middle]):
    confid = "outer"
    z = Float(3.0, "outer z")


#############################################################################
# Flat inheritance
#############################################################################


class TestInheritance:
    def test_child_has_parent_fields(self):
        class Parent(Config):
            a = Int(1, "doc")

        class Child(Parent):
            b = Int(2, "doc")

        c = Child()
        assert c.a == 1
        assert c.b == 2

    def test_child_overrides_parent_field(self):
        class Parent(Config):
            x = Float(1.0, "doc")

        class Child(Parent):
            x = Float(99.0, "overridden")

        c = Child()
        assert c.x == 99.0

    def test_grandchild_inherits_all_levels(self):
        class A(Config):
            a = Int(1, "doc")

        class B(A):
            b = Int(2, "doc")

        class C(B):
            c = Int(3, "doc")

        obj = C()
        assert obj.a == 1
        assert obj.b == 2
        assert obj.c == 3

    def test_parent_instance_unaffected_by_child(self):
        class Parent(Config):
            x = Float(1.0, "doc")

        class Child(Parent):
            x = Float(99.0, "overridden")

        parent = Parent()
        child = Child()
        assert parent.x == 1.0
        assert child.x == 99.0


#############################################################################
# components= composition
#############################################################################


class TestComponents:
    def test_nested_sub_config_accessible(self):
        class A(Config):
            confid = "a"
            v = Float(1.0, "doc")

        class B(Config, components=[A]):
            pass

        b = B()
        assert b.a.v == 1.0

    def test_instances_are_independent(self):
        class A(Config):
            confid = "a"
            v = Float(1.0, "doc")

        class B(Config, components=[A]):
            pass

        b1, b2 = B(), B()
        b1.a.v = 5.0
        assert b2.a.v == 1.0

    def test_nested_config_has_own_fields(self):
        m = Middle()
        assert m.y == 2.0
        assert m.inner.x == 1.0

    def test_deeply_nested(self):
        o = Outer()
        assert o.z == 3.0
        assert o.middle.y == 2.0
        assert o.middle.inner.x == 1.0

    def test_duplicate_confid_raises(self):
        class A(Config):
            confid = "dup"
            v = Float(1.0, "doc")

        class B(Config):
            confid = "dup"
            v = Float(2.0, "doc")

        with pytest.raises(ValueError, match="Duplicate"):

            class C(Config, components=[A, B]):
                pass

    def test_multiple_components(self):
        class Search(Config):
            confid = "search"
            n_sigma = Float(5.0, "doc")

        class Output(Config):
            confid = "output"
            path = String("./out", "doc")

        class Pipeline(Config, components=[Search, Output]):
            pass

        p = Pipeline()
        assert p.search.n_sigma == 5.0
        assert p.output.path == "./out"


#############################################################################
# Bug fix: inheritance + components= do not discard parent fields
#############################################################################


class TestInheritancePlusComponents:
    def test_child_keeps_parent_fields_when_adding_components(self):
        """Regression: components= on a child was silently discarding
        fields inherited from the parent class."""

        class ParentFlat(Config):
            alpha = Float(1.0, "alpha")
            beta = Int(10, "beta")

        class Sub(Config):
            confid = "sub"
            x = Float(0.0, "doc")

        class Child(ParentFlat, components=[Sub]):
            gamma = Float(3.0, "gamma")

        c = Child()
        assert c.alpha == 1.0
        assert c.beta == 10
        assert c.gamma == 3.0
        assert c.sub.x == 0.0

    def test_parent_with_components_child_adds_own_fields(self):
        """Child of a composed parent keeps sub-configs and adds its own."""

        class A(Config):
            confid = "a"
            v = Float(1.0, "doc")

        class Parent(Config, components=[A]):
            p_field = Float(9.0, "doc")

        class Child(Parent):
            c_field = Float(7.0, "child field")

        c = Child()
        assert c.p_field == 9.0
        assert c.c_field == 7.0

    def test_child_components_do_not_replace_parent_components(self):
        """A child that adds components= still has inherited flat fields."""

        class ParentFlat(Config):
            level = String("top", "level indicator")

        class Sub(Config):
            confid = "sub"
            x = Float(0.0, "doc")

        class Child(ParentFlat, components=[Sub]):
            pass

        c = Child()
        assert c.level == "top"
        assert c.sub.x == 0.0

    def test_fields_dict_contains_all_inherited_and_own(self):
        class Base(Config):
            a = Float(1.0, "a")

        class Sub(Config):
            confid = "sub"
            x = Float(0.0, "x")

        class Child(Base, components=[Sub]):
            b = Float(2.0, "b")

        assert "a" in Child._fields
        assert "b" in Child._fields

    def test_three_level_inheritance_plus_components(self):
        class A(Config):
            a = Int(1, "a")

        class B(A):
            b = Int(2, "b")

        class Nested(Config):
            confid = "nested"
            n = Int(99, "n")

        class C(B, components=[Nested]):
            c = Int(3, "c")

        obj = C()
        assert obj.a == 1
        assert obj.b == 2
        assert obj.c == 3
        assert obj.nested.n == 99


#############################################################################
# validate() is called after update()
#############################################################################


class TestValidateAfterUpdate:
    def test_validate_called_after_update(self):
        class C(Config):
            lo = Float(0.0, "lower bound")
            hi = Float(1.0, "upper bound")

            def validate(self):
                if self.lo >= self.hi:
                    raise ValueError(
                        f"lo must be < hi, got {self.lo} >= {self.hi}"
                    )

        c = C()
        with pytest.raises(ValueError, match="lo must be"):
            c.update({"lo": 5.0, "hi": 1.0})

    def test_valid_update_does_not_raise(self):
        class C(Config):
            lo = Float(0.0, "lower bound")
            hi = Float(1.0, "upper bound")

            def validate(self):
                if self.lo >= self.hi:
                    raise ValueError("lo must be < hi")

        c = C()
        c.update({"lo": 0.1, "hi": 0.9})
        assert c.lo == 0.1
        assert c.hi == 0.9
