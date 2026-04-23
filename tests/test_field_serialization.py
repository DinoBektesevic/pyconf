"""Tests for serialize() and deserialize() on each ConfigField subclass."""

import datetime
import pathlib

import pytest

from cfx import (
    Any,
    Bool,
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

#############################################################################
# Base ConfigField - serialize/deserialize are identity
#############################################################################


class TestBaseSerializeDeserialize:
    def test_serialize_identity(self):
        f = ConfigField(42, "doc")
        assert f.serialize(42) == 42
        assert f.serialize("hello") == "hello"

    def test_deserialize_identity(self):
        f = ConfigField(42, "doc")
        assert f.deserialize(99) == 99
        assert f.deserialize(None) is None


#############################################################################
# Path
#############################################################################


class TestPathSerializeDeserialize:
    def test_serialize_returns_str(self):
        f = Path("./out", "doc")
        result = f.serialize(pathlib.Path("/tmp/results"))
        assert isinstance(result, str)
        assert result == "/tmp/results"

    def test_deserialize_returns_path(self):
        f = Path("./out", "doc")
        result = f.deserialize("/tmp/results")
        assert isinstance(result, pathlib.Path)
        assert result == pathlib.Path("/tmp/results")

    def test_round_trip(self):
        f = Path("./out", "doc")
        original = pathlib.Path("/home/user/data")
        assert f.deserialize(f.serialize(original)) == original


#############################################################################
# MultiOptions
#############################################################################


class TestMultiOptionsSerializeDeserialize:
    def test_serialize_returns_sorted_list(self):
        f = MultiOptions(("a", "b", "c"), "doc", default_value=set())
        result = f.serialize({"c", "a"})
        assert isinstance(result, list)
        assert result == ["a", "c"]

    def test_deserialize_list_to_set(self):
        f = MultiOptions(("a", "b", "c"), "doc", default_value=set())
        result = f.deserialize(["a", "b"])
        assert isinstance(result, set)
        assert result == {"a", "b"}

    def test_deserialize_set_unchanged(self):
        f = MultiOptions(("a", "b"), "doc", default_value=set())
        s = {"a"}
        result = f.deserialize(s)
        assert result == s

    def test_round_trip(self):
        f = MultiOptions(("x", "y", "z"), "doc", default_value=set())
        original = {"x", "z"}
        assert f.deserialize(f.serialize(original)) == original


#############################################################################
# Range
#############################################################################


class TestRangeSerializeDeserialize:
    def test_serialize_returns_list(self):
        f = Range((0.0, 1.0), "doc")
        result = f.serialize((0.5, 2.0))
        assert isinstance(result, list)
        assert result == [0.5, 2.0]

    def test_deserialize_list_to_tuple(self):
        f = Range((0.0, 1.0), "doc")
        result = f.deserialize([0.5, 2.0])
        assert isinstance(result, tuple)
        assert result == (0.5, 2.0)

    def test_deserialize_tuple_unchanged(self):
        f = Range((0.0, 1.0), "doc")
        t = (0.0, 1.0)
        result = f.deserialize(t)
        assert result == t

    def test_round_trip(self):
        f = Range((0.0, 1.0), "doc")
        original = (1.5, 9.9)
        assert f.deserialize(f.serialize(original)) == original


#############################################################################
# List
#############################################################################


class TestListSerializeDeserialize:
    def test_serialize_returns_list(self):
        f = List([1, 2, 3], "doc")
        result = f.serialize([10, 20])
        assert isinstance(result, list)
        assert result == [10, 20]

    def test_deserialize_non_list_to_list(self):
        f = List([], "doc")
        result = f.deserialize((1, 2, 3))
        assert isinstance(result, list)
        assert result == [1, 2, 3]

    def test_deserialize_list_unchanged(self):
        f = List([], "doc")
        lst = [4, 5]
        result = f.deserialize(lst)
        assert result is lst


#############################################################################
# Date
#############################################################################


class TestDateSerializeDeserialize:
    def test_serialize_returns_iso_string(self):
        f = Date(datetime.date(2020, 1, 1), "doc")
        result = f.serialize(datetime.date(2024, 6, 15))
        assert isinstance(result, str)
        assert result == "2024-06-15"

    def test_deserialize_string_to_date(self):
        f = Date(datetime.date(2020, 1, 1), "doc")
        result = f.deserialize("2024-06-15")
        assert isinstance(result, datetime.date)
        assert result == datetime.date(2024, 6, 15)

    def test_deserialize_date_unchanged(self):
        f = Date(datetime.date(2020, 1, 1), "doc")
        d = datetime.date(2020, 1, 1)
        assert f.deserialize(d) == d

    def test_round_trip(self):
        f = Date(datetime.date(2020, 1, 1), "doc")
        original = datetime.date(2024, 3, 21)
        assert f.deserialize(f.serialize(original)) == original


#############################################################################
# Time
#############################################################################


class TestTimeSerializeDeserialize:
    def test_serialize_returns_iso_string(self):
        f = Time(datetime.time(0, 0), "doc")
        result = f.serialize(datetime.time(14, 30, 0))
        assert isinstance(result, str)
        assert result == "14:30:00"

    def test_deserialize_string_to_time(self):
        f = Time(datetime.time(0, 0), "doc")
        result = f.deserialize("09:00:00")
        assert isinstance(result, datetime.time)
        assert result == datetime.time(9, 0, 0)

    def test_round_trip(self):
        f = Time(datetime.time(0, 0), "doc")
        original = datetime.time(22, 15, 30)
        assert f.deserialize(f.serialize(original)) == original


#############################################################################
# DateTime
#############################################################################


class TestDateTimeSerializeDeserialize:
    def test_serialize_returns_iso_string(self):
        f = DateTime(datetime.datetime(2020, 1, 1), "doc")
        result = f.serialize(datetime.datetime(2024, 6, 15, 9, 30))
        assert isinstance(result, str)
        assert result == "2024-06-15T09:30:00"

    def test_deserialize_string_to_datetime(self):
        f = DateTime(datetime.datetime(2020, 1, 1), "doc")
        result = f.deserialize("2024-06-15T09:30:00")
        assert isinstance(result, datetime.datetime)
        assert result == datetime.datetime(2024, 6, 15, 9, 30)

    def test_round_trip(self):
        f = DateTime(datetime.datetime(2020, 1, 1), "doc")
        original = datetime.datetime(2023, 12, 31, 23, 59, 59)
        assert f.deserialize(f.serialize(original)) == original


#############################################################################
# Other field types have default (identity) serialize/deserialize
#############################################################################


class TestIdentitySerializeDeserialize:
    @pytest.mark.parametrize(
        "field, value",
        [
            (String("x", "doc"), "hello"),
            (Int(0, "doc"), 42),
            (Float(0.0, "doc"), 3.14),
            (Bool(False, "doc"), True),
            (Scalar(1.0, "doc"), 2.5),
            (Seed(None, "doc"), 99),
            (Options(("a", "b"), "doc"), "a"),
            (Dict({}, "doc"), {"k": "v"}),
            (Any(None, "doc"), [1, 2, 3]),
        ],
    )
    def test_serialize_identity(self, field, value):
        assert field.serialize(value) == value

    @pytest.mark.parametrize(
        "field, value",
        [
            (String("x", "doc"), "hello"),
            (Int(0, "doc"), 42),
            (Float(0.0, "doc"), 3.14),
            (Bool(False, "doc"), True),
            (Options(("a", "b"), "doc"), "a"),
            (Dict({}, "doc"), {"k": "v"}),
        ],
    )
    def test_deserialize_identity(self, field, value):
        assert field.deserialize(value) == value
