"""Tests for ConfigField and all typed field descriptors."""

import datetime
import pathlib

import pytest

from cfx import (
    Bool,
    Config,
    ConfigField,
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

# ---------------------------------------------------------------------------
# ConfigField - base descriptor behaviour
# ---------------------------------------------------------------------------


class TestConfigField:
    def test_default_value_returned_before_assignment(self):
        class C(Config):
            f = ConfigField("default", "doc")

        assert C().f == "default"

    def test_set_and_get(self):
        class C(Config):
            f = ConfigField("x", "doc")

        c = C()
        c.f = "y"
        assert c.f == "y"

    def test_instances_are_independent(self):
        class C(Config):
            f = ConfigField("x", "doc")

        c1, c2 = C(), C()
        c1.f = "changed"
        assert c2.f == "x"

    def test_class_access_returns_descriptor(self):
        class C(Config):
            f = ConfigField("x", "doc")

        assert isinstance(C.f, ConfigField)

    def test_static_field_cannot_be_set(self):
        class C(Config):
            f = ConfigField("x", "doc", static=True)

        with pytest.raises(AttributeError):
            C().f = "y"

    def test_static_field_returns_default(self):
        class C(Config):
            f = ConfigField("x", "doc", static=True)

        c = C()
        assert c.f == "x"

    def test_lazy_default_callable(self):
        class C(Config):
            base = Float(2.0, "base value")
            derived = Float(lambda self: self.base * 3, "triple base")

        c = C()
        assert c.derived == 6.0
        c.base = 4.0
        assert c.derived == 12.0  # recomputes from current base

    def test_lazy_default_overrideable(self):
        class C(Config):
            base = Float(2.0, "base")
            derived = Float(lambda self: self.base * 3, "derived")

        c = C()
        c.derived = 99.0
        assert c.derived == 99.0  # stored value, not recomputed


# ---------------------------------------------------------------------------
# String
# ---------------------------------------------------------------------------


class TestString:
    def test_accepts_string(self):
        class C(Config):
            f = String("hello", "doc")

        c = C()
        c.f = "world"
        assert c.f == "world"

    def test_rejects_non_string(self):
        class C(Config):
            f = String("hello", "doc")

        with pytest.raises(TypeError):
            C().f = 123

    def test_minsize(self):
        class C(Config):
            f = String("ab", "doc", minsize=2)

        with pytest.raises(ValueError):
            C().f = "x"

    def test_maxsize(self):
        class C(Config):
            f = String("hi", "doc", maxsize=3)

        with pytest.raises(ValueError):
            C().f = "toolong"

    def test_predicate(self):
        class C(Config):
            f = String("abc", "doc", predicate=str.islower)

        with pytest.raises(ValueError):
            C().f = "ABC"


# ---------------------------------------------------------------------------
# Int
# ---------------------------------------------------------------------------


class TestInt:
    def test_accepts_int(self):
        class C(Config):
            f = Int(1, "doc")

        c = C()
        c.f = 5
        assert c.f == 5

    def test_rejects_float(self):
        class C(Config):
            f = Int(1, "doc")

        with pytest.raises(TypeError):
            C().f = 1.5

    def test_minval(self):
        class C(Config):
            f = Int(1, "doc", minval=0)

        with pytest.raises(ValueError):
            C().f = -1

    def test_maxval(self):
        class C(Config):
            f = Int(1, "doc", maxval=10)

        with pytest.raises(ValueError):
            C().f = 11

    def test_rejects_bool(self):
        class C(Config):
            f = Int(1, "doc")

        with pytest.raises(TypeError):
            C().f = True


# ---------------------------------------------------------------------------
# Float
# ---------------------------------------------------------------------------


class TestFloat:
    def test_accepts_float(self):
        class C(Config):
            f = Float(1.0, "doc")

        c = C()
        c.f = 2.5
        assert c.f == 2.5

    def test_accepts_int_as_float(self):
        class C(Config):
            f = Float(1.0, "doc")

        C().f = 2  # ints are accepted for Float

    def test_rejects_string(self):
        class C(Config):
            f = Float(1.0, "doc")

        with pytest.raises(TypeError):
            C().f = "1.0"

    def test_minval(self):
        class C(Config):
            f = Float(1.0, "doc", minval=0.0)

        with pytest.raises(ValueError):
            C().f = -0.1

    def test_rejects_bool(self):
        class C(Config):
            f = Float(1.0, "doc")

        with pytest.raises(TypeError):
            C().f = False


# ---------------------------------------------------------------------------
# Scalar
# ---------------------------------------------------------------------------


class TestScalar:
    def test_accepts_int_and_float(self):
        class C(Config):
            f = Scalar(1, "doc")

        c = C()
        c.f = 2
        c.f = 2.5

    def test_rejects_string(self):
        class C(Config):
            f = Scalar(1, "doc")

        with pytest.raises(TypeError):
            C().f = "x"


# ---------------------------------------------------------------------------
# Bool
# ---------------------------------------------------------------------------


class TestBool:
    def test_accepts_bool(self):
        class C(Config):
            f = Bool(False, "doc")

        c = C()
        c.f = True
        assert c.f is True

    def test_rejects_int(self):
        class C(Config):
            f = Bool(False, "doc")

        with pytest.raises(TypeError):
            C().f = 1  # int is not bool


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


class TestOptions:
    def test_default_is_first_option(self):
        class C(Config):
            f = Options(("x", "y", "z"), "doc")

        assert C().f == "x"

    def test_custom_default(self):
        class C(Config):
            f = Options(("x", "y", "z"), "doc", default_value="y")

        assert C().f == "y"

    def test_accepts_valid_option(self):
        class C(Config):
            f = Options(("x", "y"), "doc")

        c = C()
        c.f = "y"
        assert c.f == "y"

    def test_rejects_invalid_option(self):
        class C(Config):
            f = Options(("x", "y"), "doc")

        with pytest.raises(ValueError):
            C().f = "z"


# ---------------------------------------------------------------------------
# MultiOptions
# ---------------------------------------------------------------------------


class TestMultiOptions:
    def test_accepts_valid_subset(self):
        class C(Config):
            f = MultiOptions(("a", "b", "c"), "doc", default_value=set())

        c = C()
        c.f = {"a", "c"}
        assert c.f == {"a", "c"}

    def test_coerces_list_to_set(self):
        # Lists are coerced to sets so that YAML/TOML round-trips work
        # (those formats deserialize sequences as lists, not sets).
        class C(Config):
            f = MultiOptions(("a", "b"), "doc", default_value=set())

        c = C()
        c.f = ["a", "b"]
        assert c.f == {"a", "b"}
        assert isinstance(c.f, set)

    def test_rejects_out_of_set_members(self):
        class C(Config):
            f = MultiOptions(("a", "b"), "doc", default_value=set())

        with pytest.raises(ValueError):
            C().f = {"a", "z"}

    def test_empty_set_is_valid(self):
        class C(Config):
            f = MultiOptions(("a", "b"), "doc", default_value=set())

        c = C()
        c.f = set()


# ---------------------------------------------------------------------------
# Path
# ---------------------------------------------------------------------------


class TestPath:
    def test_coerces_string_to_path(self):
        class C(Config):
            f = Path("./out", "doc")

        c = C()
        c.f = "./results"
        assert isinstance(c.f, pathlib.Path)

    def test_accepts_path_object(self):
        class C(Config):
            f = Path("./out", "doc")

        c = C()
        c.f = pathlib.Path("./results")
        assert c.f == pathlib.Path("./results")

    def test_must_exist_raises_for_missing_path(self, tmp_path):
        class C(Config):
            f = Path(tmp_path, "doc", must_exist=True)

        with pytest.raises(ValueError):
            C().f = pathlib.Path("/nonexistent/path/xyz")

    def test_must_exist_accepts_real_path(self, tmp_path):
        class C(Config):
            f = Path(tmp_path, "doc", must_exist=True)

        c = C()
        c.f = tmp_path  # tmp_path exists

    def test_validate_rejects_non_path(self):
        class C(Config):
            f = Path("./out", "doc")

        with pytest.raises(TypeError):
            C.f.validate(42)

    def test_string_default_normalized_to_path(self):
        class C(Config):
            f = Path("./out", "doc")

        assert isinstance(C.f.defaultval, pathlib.Path)


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


class TestSeed:
    def test_accepts_int(self):
        class C(Config):
            f = Seed(0, "doc")

        c = C()
        c.f = 123
        assert c.f == 123

    def test_accepts_none(self):
        class C(Config):
            f = Seed(None, "doc")

        c = C()
        c.f = None
        assert c.f is None

    def test_rejects_float(self):
        class C(Config):
            f = Seed(None, "doc")

        with pytest.raises(TypeError):
            C().f = 1.5


# ---------------------------------------------------------------------------
# Range
# ---------------------------------------------------------------------------


class TestRange:
    def test_accepts_valid_range(self):
        class C(Config):
            f = Range((0.0, 1.0), "doc")

        c = C()
        c.f = (0.0, 5.0)
        assert c.f == (0.0, 5.0)

    def test_rejects_equal_bounds(self):
        class C(Config):
            f = Range((0.0, 1.0), "doc")

        with pytest.raises(ValueError):
            C().f = (1.0, 1.0)

    def test_rejects_inverted_bounds(self):
        class C(Config):
            f = Range((0.0, 1.0), "doc")

        with pytest.raises(ValueError):
            C().f = (5.0, 1.0)

    def test_rejects_non_pair(self):
        class C(Config):
            f = Range((0.0, 1.0), "doc")

        with pytest.raises(TypeError):
            C().f = 1.0


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class TestList:
    def test_accepts_list(self):
        class C(Config):
            f = List([], "doc")

        c = C()
        c.f = [1, 2, 3]
        assert c.f == [1, 2, 3]

    def test_rejects_non_list(self):
        class C(Config):
            f = List([], "doc")

        with pytest.raises(TypeError):
            C().f = {1, 2}

    def test_element_type_check(self):
        class C(Config):
            f = List([], "doc", element_type=int)

        with pytest.raises(TypeError):
            C().f = [1, "two", 3]

    def test_minlen(self):
        class C(Config):
            f = List([1, 2], "doc", minlen=2)

        with pytest.raises(ValueError):
            C().f = [1]

    def test_maxlen(self):
        class C(Config):
            f = List([1], "doc", maxlen=2)

        with pytest.raises(ValueError):
            C().f = [1, 2, 3]


# ---------------------------------------------------------------------------
# Dict
# ---------------------------------------------------------------------------


class TestDict:
    def test_accepts_dict(self):
        class C(Config):
            f = Dict({}, "doc")

        c = C()
        c.f = {"key": "value"}
        assert c.f == {"key": "value"}

    def test_rejects_non_dict(self):
        class C(Config):
            f = Dict({}, "doc")

        with pytest.raises(TypeError):
            C().f = [("key", "value")]


# ---------------------------------------------------------------------------
# Date / Time / DateTime
# ---------------------------------------------------------------------------


class TestDateTimeFields:
    def test_date_accepts_date(self):
        class C(Config):
            f = Date(datetime.date(2020, 1, 1), "doc")

        c = C()
        c.f = datetime.date(2021, 6, 15)
        assert c.f == datetime.date(2021, 6, 15)

    def test_date_rejects_string(self):
        class C(Config):
            f = Date(datetime.date(2020, 1, 1), "doc")

        with pytest.raises(TypeError):
            C().f = "2021-06-15"

    def test_time_accepts_time(self):
        class C(Config):
            f = Time(datetime.time(0, 0), "doc")

        c = C()
        c.f = datetime.time(12, 30)

    def test_time_coerces_iso_string(self):
        # ISO strings are coerced so dict/YAML round-trips work transparently.
        class C(Config):
            f = Time(datetime.time(0, 0), "doc")

        c = C()
        c.f = "12:30:00"
        assert c.f == datetime.time(12, 30)

    def test_time_rejects_non_time_non_string(self):
        class C(Config):
            f = Time(datetime.time(0, 0), "doc")

        with pytest.raises(TypeError):
            C().f = 1230  # int is not a time or ISO string

    def test_datetime_accepts_datetime(self):
        class C(Config):
            f = DateTime(datetime.datetime(2020, 1, 1), "doc")

        c = C()
        c.f = datetime.datetime(2021, 6, 15, 12, 0)

    def test_datetime_rejects_date(self):
        class C(Config):
            f = DateTime(datetime.datetime(2020, 1, 1), "doc")

        with pytest.raises(TypeError):
            C().f = datetime.date(2021, 6, 15)


# ---------------------------------------------------------------------------
# env= parameter - environment variable fallback
# ---------------------------------------------------------------------------


class TestEnvVar:
    """Priority chain: explicit assignment > env var > default."""

    def test_int_reads_env(self, monkeypatch):
        monkeypatch.setenv("MY_INT", "42")

        class C(Config):
            f = Int(0, "doc", env="MY_INT")

        assert C().f == 42

    def test_float_reads_env(self, monkeypatch):
        monkeypatch.setenv("MY_FLOAT", "3.14")

        class C(Config):
            f = Float(0.0, "doc", env="MY_FLOAT")

        assert C().f == pytest.approx(3.14)

    def test_bool_true_variants(self, monkeypatch):
        class C(Config):
            f = Bool(False, "doc", env="MY_BOOL")

        for val in ("1", "true", "True", "yes", "on"):
            monkeypatch.setenv("MY_BOOL", val)
            assert C().f is True, f"Expected True for {val!r}"

    def test_bool_false_variants(self, monkeypatch):
        class C(Config):
            f = Bool(False, "doc", env="MY_BOOL")

        for val in ("0", "false", "False", "no", "off"):
            monkeypatch.setenv("MY_BOOL", val)
            assert C().f is False, f"Expected False for {val!r}"

    def test_string_reads_env(self, monkeypatch):
        monkeypatch.setenv("MY_STR", "hello")

        class C(Config):
            f = String("default", "doc", env="MY_STR")

        assert C().f == "hello"

    def test_options_reads_env(self, monkeypatch):
        monkeypatch.setenv("MY_OPT", "b")

        class C(Config):
            f = Options(("a", "b", "c"), "doc", env="MY_OPT")

        assert C().f == "b"

    def test_options_env_rejects_invalid(self, monkeypatch):
        monkeypatch.setenv("MY_OPT", "z")

        class C(Config):
            f = Options(("a", "b"), "doc", env="MY_OPT")

        with pytest.raises(ValueError):
            _ = C().f  # access triggers env read + validate

    def test_path_reads_env(self, monkeypatch):
        monkeypatch.setenv("MY_PATH", "/tmp/out")

        class C(Config):
            f = Path("./default", "doc", env="MY_PATH")

        assert C().f == pathlib.Path("/tmp/out")

    def test_seed_reads_int(self, monkeypatch):
        monkeypatch.setenv("MY_SEED", "99")

        class C(Config):
            f = Seed(0, "doc", env="MY_SEED")

        assert C().f == 99

    def test_seed_reads_none(self, monkeypatch):
        monkeypatch.setenv("MY_SEED", "none")

        class C(Config):
            f = Seed(0, "doc", env="MY_SEED")

        assert C().f is None

    def test_multioptions_reads_env(self, monkeypatch):
        monkeypatch.setenv("MY_MULTI", "a, c")

        class C(Config):
            f = MultiOptions(("a", "b", "c"), "doc", env="MY_MULTI")

        assert C().f == {"a", "c"}

    def test_range_reads_env(self, monkeypatch):
        monkeypatch.setenv("MY_RANGE", "0.0,1.0")

        class C(Config):
            f = Range((0.0, 10.0), "doc", env="MY_RANGE")

        assert C().f == (0.0, 1.0)

    def test_explicit_assignment_overrides_env(self, monkeypatch):
        monkeypatch.setenv("MY_INT", "99")

        class C(Config):
            f = Int(0, "doc", env="MY_INT")

        c = C()
        c.f = 7
        assert c.f == 7  # stored value wins over env

    def test_default_used_when_env_absent(self):
        class C(Config):
            f = Int(42, "doc", env="DEFINITELY_NOT_SET_XYZ")

        assert C().f == 42

    def test_env_absent_falls_through_to_default(self):
        class C(Config):
            f = Float(1.5, "doc", env="DEFINITELY_NOT_SET_XYZ")

        assert C().f == 1.5

    def test_env_value_not_stored_in_dict(self, monkeypatch):
        """Env var values are not persisted - re-read on every access."""
        monkeypatch.setenv("MY_INT", "10")

        class C(Config):
            f = Int(0, "doc", env="MY_INT")

        c = C()
        _ = c.f  # access it
        descriptor = type(c).f
        assert descriptor.private_name not in c.__dict__


# ---------------------------------------------------------------------------
# Transient fields
# ---------------------------------------------------------------------------


class TestTransient:
    def test_callable_default_skipped_in_to_dict(self):
        class C(Config):
            base = Float(1.0, "base")
            derived = Float(lambda self: self.base * 3, "3x base")

        d = C().to_dict()
        assert "derived" not in d
        assert "base" in d

    def test_callable_with_stored_value_serialized(self):
        class C(Config):
            base = Float(1.0, "base")
            derived = Float(lambda self: self.base * 3, "3x base")

        cfg = C()
        cfg.derived = 99.0
        d = cfg.to_dict()
        assert d["derived"] == 99.0

    def test_transient_false_on_callable_serializes_snapshot(self):
        class C(Config):
            base = Float(1.0, "base")
            derived = Float(
                lambda self: self.base * 3, "3x base", transient=False
            )

        d = C().to_dict()
        assert "derived" in d
        assert d["derived"] == 3.0

    def test_transient_true_on_noncallable_skipped(self):
        class C(Config):
            base = Float(1.0, "base")
            hidden = Float(0.0, "not serialized", transient=True)

        d = C().to_dict()
        assert "hidden" not in d

    def test_transient_true_noncallable_serialized_when_stored(self):
        class C(Config):
            hidden = Float(0.0, "not serialized by default", transient=True)

        cfg = C()
        cfg.hidden = 7.0
        assert cfg.to_dict()["hidden"] == 7.0

    def test_round_trip_callable_default_survives(self):
        class C(Config):
            base = Float(2.0, "base")
            derived = Float(lambda self: self.base * 5, "5x base")

        cfg = C()
        d = cfg.to_dict()
        cfg2 = C.from_dict(d)
        assert cfg2.derived == 10.0  # callable still active

        cfg2.base = 4.0
        assert cfg2.derived == 20.0  # recomputes from new base

    def test_static_computed_field_skipped_in_to_dict(self):
        class C(Config):
            base = Float(1.0, "base")
            fixed = Float(lambda self: self.base * 3, "3x base", static=True)

        d = C().to_dict()
        assert "fixed" not in d
