"""Tests for to_argparse_kwargs() and to_click_option() on field types."""

import argparse
import datetime

import pytest

from cfx import (
    Bool,
    Config,
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
    Seed,
    Time,
)
from cfx.types.config_field import _CLI_UNSET

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402

#############################################################################
# Helpers
#############################################################################


def make_parser(*fields_and_names):
    """Build a parser from (field, name) pairs and return it."""
    parser = argparse.ArgumentParser()
    for descriptor, name in fields_and_names:
        descriptor.__set_name__(None, name)
        kwargs = descriptor.to_argparse_kwargs(name)
        flag = kwargs.pop("flag")
        parser.add_argument(flag, **kwargs)
    return parser


#############################################################################
# Base ConfigField to_argparse_kwargs structure
#############################################################################


class TestArgparseKwargsBase:
    def test_flag_and_dest_no_prefix(self):
        f = Float(1.0, "A float field")
        f.__set_name__(None, "n_sigma")
        kwargs = f.to_argparse_kwargs("n_sigma")
        assert kwargs["flag"] == "--n-sigma"
        assert kwargs["dest"] == "n_sigma"

    def test_flag_with_prefix(self):
        f = Float(1.0, "doc")
        f.__set_name__(None, "n_sigma")
        kwargs = f.to_argparse_kwargs("n_sigma", prefix="search")
        assert kwargs["flag"] == "--search.n-sigma"
        assert kwargs["dest"] == "search.n_sigma"

    def test_default_is_cli_unset_sentinel(self):
        f = Float(1.0, "doc")
        f.__set_name__(None, "x")
        kwargs = f.to_argparse_kwargs("x")
        assert kwargs["default"] is _CLI_UNSET

    def test_help_matches_doc(self):
        f = Float(1.0, "Detection threshold")
        f.__set_name__(None, "x")
        kwargs = f.to_argparse_kwargs("x")
        assert kwargs["help"] == "Detection threshold"

    def test_type_callable_parses_string(self):
        f = Int(0, "doc")
        f.__set_name__(None, "n")
        kwargs = f.to_argparse_kwargs("n")
        assert kwargs["type"]("42") == 42


#############################################################################
# Bool uses BooleanOptionalAction (no type key)
#############################################################################


class TestBoolArgparse:
    def test_no_type_key(self):
        f = Bool(False, "doc")
        f.__set_name__(None, "verbose")
        kwargs = f.to_argparse_kwargs("verbose")
        assert "type" not in kwargs

    def test_action_is_boolean_optional(self):
        f = Bool(False, "doc")
        f.__set_name__(None, "verbose")
        kwargs = f.to_argparse_kwargs("verbose")
        assert kwargs["action"] is argparse.BooleanOptionalAction

    def test_parses_true(self):
        parser = make_parser((Bool(False, "doc"), "verbose"))
        ns = parser.parse_args(["--verbose"])
        assert ns.verbose is True

    def test_parses_false(self):
        parser = make_parser((Bool(False, "doc"), "verbose"))
        ns = parser.parse_args(["--no-verbose"])
        assert ns.verbose is False


#############################################################################
# Options uses choices
#############################################################################


class TestOptionsArgparse:
    def test_choices_present(self):
        f = Options(("fast", "balanced", "thorough"), "doc")
        f.__set_name__(None, "mode")
        kwargs = f.to_argparse_kwargs("mode")
        assert "choices" in kwargs
        assert set(kwargs["choices"]) == {"fast", "balanced", "thorough"}

    def test_invalid_choice_rejected(self):
        parser = make_parser((Options(("a", "b", "c"), "doc"), "mode"))
        with pytest.raises(SystemExit):
            parser.parse_args(["--mode", "z"])

    def test_valid_choice_accepted(self):
        parser = make_parser((Options(("a", "b", "c"), "doc"), "mode"))
        ns = parser.parse_args(["--mode", "b"])
        assert ns.mode == "b"


#############################################################################
# MultiOptions: nargs=+, choices
#############################################################################


class TestMultiOptionsArgparse:
    def test_nargs_plus(self):
        f = MultiOptions(("a", "b", "c"), "doc", default_value=set())
        f.__set_name__(None, "steps")
        kwargs = f.to_argparse_kwargs("steps")
        assert kwargs["nargs"] == "+"

    def test_choices_present(self):
        f = MultiOptions(("a", "b", "c"), "doc", default_value=set())
        f.__set_name__(None, "steps")
        kwargs = f.to_argparse_kwargs("steps")
        assert set(kwargs["choices"]) == {"a", "b", "c"}

    def test_type_is_str(self):
        f = MultiOptions(("a", "b"), "doc", default_value=set())
        f.__set_name__(None, "steps")
        kwargs = f.to_argparse_kwargs("steps")
        assert kwargs["type"] is str

    def test_parses_multiple_values(self):
        class C(Config):
            confid = "c"
            steps = MultiOptions(("a", "b", "c"), "doc", default_value={"a"})

        parser = argparse.ArgumentParser()
        C.add_arguments(parser)
        ns = parser.parse_args(["--steps", "a", "b"])
        cfg = C.from_argparse(ns)
        assert cfg.steps == {"a", "b"}


#############################################################################
# Metavar fields
#############################################################################


class TestMetavars:
    @pytest.mark.parametrize(
        "field, name, expected_metavar",
        [
            (Seed(None, "doc"), "seed", "INT|none"),
            (Range((0.0, 1.0), "doc"), "bounds", "MIN,MAX"),
            (Path("./out", "doc"), "output", "PATH"),
            (Dict({}, "doc"), "meta", "JSON"),
            (Date(datetime.date(2020, 1, 1), "doc"), "d", "YYYY-MM-DD"),
            (Time(datetime.time(0, 0), "doc"), "t", "HH:MM:SS"),
            (
                DateTime(datetime.datetime(2020, 1, 1), "doc"),
                "dt",
                "YYYY-MM-DDTHH:MM:SS",
            ),
        ],
    )
    def test_metavar(self, field, name, expected_metavar):
        field.__set_name__(None, name)
        kwargs = field.to_argparse_kwargs(name)
        assert kwargs.get("metavar") == expected_metavar


#############################################################################
# List: nargs=+
#############################################################################


class TestListArgparse:
    def test_nargs_plus(self):
        f = List([], "doc", element_type=str)
        f.__set_name__(None, "tags")
        kwargs = f.to_argparse_kwargs("tags")
        assert kwargs["nargs"] == "+"

    def test_type_is_element_type(self):
        f = List([], "doc", element_type=int)
        f.__set_name__(None, "nums")
        kwargs = f.to_argparse_kwargs("nums")
        assert kwargs["type"] is int

    def test_type_defaults_to_str(self):
        f = List([], "doc")
        f.__set_name__(None, "items")
        kwargs = f.to_argparse_kwargs("items")
        assert kwargs["type"] is str


#############################################################################
# Click integration
#############################################################################


class TestClickBool:
    def test_flag_pair_no_prefix(self):
        f = Bool(False, "verbose flag")
        f.__set_name__(None, "verbose")
        decorator = f.to_click_option("verbose")

        @click.command()
        @decorator
        def cmd(verbose):
            click.echo(verbose)

        result = CliRunner().invoke(cmd, ["--verbose"])
        assert result.exit_code == 0
        assert "True" in result.output

        result = CliRunner().invoke(cmd, ["--no-verbose"])
        assert result.exit_code == 0
        assert "False" in result.output

    def test_flag_pair_with_prefix(self):
        f = Bool(False, "verbose flag")
        f.__set_name__(None, "verbose")
        decorator = f.to_click_option("verbose", prefix="search")

        @click.command()
        @decorator
        def cmd(**kwargs):
            click.echo(list(kwargs.values())[0])

        result = CliRunner().invoke(cmd, ["--search.verbose"])
        assert result.exit_code == 0
        assert "True" in result.output


class TestClickOptions:
    def test_choice_type(self):
        f = Options(("a", "b", "c"), "mode field")
        f.__set_name__(None, "mode")
        decorator = f.to_click_option("mode")

        @click.command()
        @decorator
        def cmd(mode):
            click.echo(mode)

        result = CliRunner().invoke(cmd, ["--mode", "b"])
        assert result.exit_code == 0
        assert "b" in result.output

    def test_invalid_choice_fails(self):
        f = Options(("a", "b", "c"), "mode field")
        f.__set_name__(None, "mode")
        decorator = f.to_click_option("mode")

        @click.command()
        @decorator
        def cmd(mode):
            click.echo(mode)

        result = CliRunner().invoke(cmd, ["--mode", "z"])
        assert result.exit_code != 0


class TestClickMultiOptions:
    def test_multiple_true(self):
        f = MultiOptions(("a", "b", "c"), "steps")
        f.__set_name__(None, "steps")
        decorator = f.to_click_option("steps")

        @click.command()
        @decorator
        def cmd(steps):
            click.echo(sorted(steps))

        result = CliRunner().invoke(cmd, ["--steps", "a", "--steps", "b"])
        assert result.exit_code == 0
        assert "a" in result.output
        assert "b" in result.output


class TestClickNoClickRaises:
    def test_raises_import_error_when_click_missing(self, monkeypatch):
        import cfx.types.config_field as cf_mod
        import cfx.types.types as types_mod

        original_click_cf = cf_mod._click
        original_click_types = types_mod._click

        cf_mod._click = None
        types_mod._click = None

        try:
            f = Float(1.0, "doc")
            f.__set_name__(None, "x")
            with pytest.raises(ImportError):
                f.to_click_option("x")
        finally:
            cf_mod._click = original_click_cf
            types_mod._click = original_click_types
