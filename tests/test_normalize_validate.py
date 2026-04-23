"""Tests for the normalize -> validate pipeline on ConfigField subclasses."""

import datetime
import pathlib

import pytest

from cfx import (
    Config,
    ConfigField,
    Date,
    DateTime,
    List,
    MultiOptions,
    Path,
    Range,
    Time,
)

#############################################################################
# Base ConfigField - normalize is identity, validate is no-op
#############################################################################


class TestBaseNormalize:
    def test_normalize_is_identity(self):
        f = ConfigField(42, "doc")
        assert f.normalize(42) == 42
        assert f.normalize("hello") == "hello"
        assert f.normalize([1, 2]) == [1, 2]

    def test_normalize_called_for_default(self):
        """normalize is called in __init__ so defaults are canonical."""

        class Coercing(ConfigField):
            def normalize(self, value):
                return str(value)

        f = Coercing(123, "doc")
        assert f.defaultval == "123"

    def test_normalize_called_on_set(self):
        """normalize must be called in __set__ before storing the value."""

        class Doubling(ConfigField):
            def normalize(self, value):
                return value * 2

        class C(Config):
            x = Doubling(1, "doc")

        c = C()
        c.x = 5
        assert c.x == 10

    def test_normalize_before_validate(self):
        """validate sees the normalized value, not the raw input.

        Proof: a raw value that would fail validate passes through unharmed
        because normalize converts it first.
        """

        class StringToInt(ConfigField):
            def normalize(self, value):
                if isinstance(value, str):
                    return int(value)
                return value

            def validate(self, value):
                if not isinstance(value, int):
                    raise TypeError(
                        f"Expected int, got {type(value).__name__!r}"
                    )

        class C(Config):
            x = StringToInt(0, "doc")

        c = C()
        # "42" is not an int, so validate alone would raise.
        # The fact that it doesn't means normalize ran first.
        c.x = "42"
        assert c.x == 42

    def test_normalize_idempotent_contract(self):
        """normalize(normalize(v)) == normalize(v) for all built-in types."""
        p = Path("./data", "doc")
        v = p.normalize("./data")
        assert p.normalize(v) == v

        r = Range((0.0, 1.0), "doc")
        v = r.normalize([0.0, 1.0])
        assert r.normalize(v) == v

        m = MultiOptions(("a", "b"), "doc", default_value=set())
        v = m.normalize(["a"])
        assert m.normalize(v) == v


#############################################################################
# MultiOptions normalize: list/tuple -> set
#############################################################################


class TestMultiOptionsNormalize:
    def test_tuple_coerced_to_set(self):
        f = MultiOptions(("a", "b", "c"), "doc", default_value=set())
        assert f.normalize(("b", "c")) == {"b", "c"}

    def test_set_unchanged(self):
        f = MultiOptions(("a", "b"), "doc", default_value=set())
        s = {"a"}
        assert f.normalize(s) is s

    def test_invalid_still_passes_normalize(self):
        """normalize does not validate; validate catches invalid values."""
        f = MultiOptions(("a", "b"), "doc", default_value=set())
        # list -> set conversion happens; validate() rejects unknown elements
        normalized = f.normalize(["z"])
        assert normalized == {"z"}
        with pytest.raises(ValueError):
            f.validate(normalized)


#############################################################################
# Path normalize: str/os.PathLike -> pathlib.Path
#############################################################################


class TestPathNormalize:
    def test_string_coerced(self):
        f = Path("./out", "doc")
        assert f.normalize("./out") == pathlib.Path("./out")

    def test_path_unchanged(self):
        f = Path("./out", "doc")
        p = pathlib.Path("./out")
        assert f.normalize(p) == p

    def test_invalid_returns_value_unchanged(self):
        f = Path("./out", "doc")
        assert f.normalize(42) == 42


#############################################################################
# Range normalize: list -> tuple
#############################################################################


class TestRangeNormalize:
    def test_list_coerced_to_tuple(self):
        f = Range((0.0, 1.0), "doc")
        result = f.normalize([0.0, 1.0])
        assert result == (0.0, 1.0)
        assert isinstance(result, tuple)

    def test_tuple_unchanged(self):
        f = Range((0.0, 1.0), "doc")
        t = (0.0, 1.0)
        assert f.normalize(t) is t

    def test_default_stored_as_tuple(self):
        f = Range((0.0, 1.0), "doc")
        assert isinstance(f.defaultval, tuple)


#############################################################################
# List normalize: tuple -> list
#############################################################################


class TestListNormalize:
    def test_tuple_coerced_to_list(self):
        f = List([], "doc")
        result = f.normalize((1, 2, 3))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_list_unchanged(self):
        f = List([], "doc")
        lst = [1, 2]
        assert f.normalize(lst) is lst


#############################################################################
# Date/Time/DateTime normalize: ISO string -> datetime object
#############################################################################


class TestDateNormalize:
    def test_iso_string_coerced(self):
        f = Date(datetime.date(2020, 1, 1), "doc")
        result = f.normalize("2024-06-15")
        assert result == datetime.date(2024, 6, 15)

    def test_date_unchanged(self):
        f = Date(datetime.date(2020, 1, 1), "doc")
        d = datetime.date(2020, 1, 1)
        assert f.normalize(d) == d


class TestTimeNormalize:
    def test_iso_string_coerced(self):
        f = Time(datetime.time(0, 0), "doc")
        assert f.normalize("09:30:00") == datetime.time(9, 30, 0)

    def test_time_unchanged(self):
        f = Time(datetime.time(0, 0), "doc")
        t = datetime.time(12, 0)
        assert f.normalize(t) == t


class TestDateTimeNormalize:
    def test_iso_string_coerced(self):
        f = DateTime(datetime.datetime(2020, 1, 1), "doc")
        result = f.normalize("2024-06-15T09:30:00")
        assert result == datetime.datetime(2024, 6, 15, 9, 30, 0)

    def test_datetime_unchanged(self):
        f = DateTime(datetime.datetime(2020, 1, 1), "doc")
        dt = datetime.datetime(2020, 1, 1)
        assert f.normalize(dt) == dt


#############################################################################
# Custom field example: Angle wraps to [0, 360)
#############################################################################


class Angle(ConfigField[float]):
    def normalize(self, value):
        return float(value) % 360.0

    def validate(self, value):
        if not isinstance(value, float):
            raise TypeError(f"Expected float, got {type(value).__name__!r}")


class TestCustomFieldNormalizeValidate:
    def test_angle_wraps_on_set(self):
        class C(Config):
            bearing = Angle(0.0, "compass bearing")

        c = C()
        c.bearing = 370.0
        assert c.bearing == 10.0

    def test_angle_negative_wraps(self):
        class C(Config):
            bearing = Angle(0.0, "compass bearing")

        c = C()
        c.bearing = -90.0
        assert c.bearing == 270.0

    def test_angle_default_normalized(self):
        class C(Config):
            bearing = Angle(720.0, "compass bearing")

        c = C()
        assert c.bearing == 0.0

    def test_angle_validates_after_normalize(self):
        """validate sees float because normalize calls float() first."""

        class C(Config):
            bearing = Angle(0.0, "compass bearing")

        c = C()
        c.bearing = 45  # int; normalize coerces to 45.0 before validate
        assert c.bearing == 45.0

    def test_validate_rejects_non_numeric(self):
        class C(Config):
            bearing = Angle(0.0, "compass bearing")

        c = C()
        with pytest.raises((TypeError, ValueError)):
            c.bearing = "north"
