"""Tests for CLI integration: argparse and click round-trips."""

import argparse
import datetime
import pathlib

import pytest

from cfx import (
    Config,
    Bool,
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
# Helpers
# ---------------------------------------------------------------------------

def parse(cfg_cls, argv):
    """Parse *argv* into a `Config` instance via argparse."""
    parser = argparse.ArgumentParser()
    cfg_cls.add_arguments(parser)
    return cfg_cls.from_argparse(parser.parse_args(argv))


# ---------------------------------------------------------------------------
# Config classes used in CLI tests
# ---------------------------------------------------------------------------

class FlatConfig(Config):
    confid = "flat"
    n_sigma = Float(5.0, "Detection threshold")
    iterations = Int(100, "Number of iterations", minval=1)
    label = String("run01", "Run label")
    mode = Options(("fast", "balanced", "thorough"), "Processing mode")
    verbose = Bool(False, "Enable verbose output")
    scale = Scalar(1.0, "Scaling factor")
    seed = Seed(None, "RNG seed")
    bounds = Range((0.0, 1.0), "Value bounds")
    steps = MultiOptions(
        ("a", "b", "c"), "Pipeline steps", default_value={"a"}
    )
    output = Path("./out", "Output directory")
    meta = Dict({}, "Metadata dict")
    tags = List([], "Tag list", element_type=str)
    start_date = Date(datetime.date(2024, 1, 1), "Start date")
    start_time = Time(datetime.time(0, 0), "Start time")
    start_dt = DateTime(datetime.datetime(2024, 1, 1, 0, 0), "Start datetime")
    static_val = Int(42, "A static field", static=True)


class SearchConfig(Config):
    confid = "search"
    n_sigma = Float(5.0, "Detection threshold")
    verbose = Bool(False, "Verbose search")


class OutputConfig(Config):
    confid = "output"
    directory = Path("./results", "Output directory")
    compress = Bool(False, "Compress output")


class PipelineConfig(
    Config, components=[SearchConfig, OutputConfig], method="nested"
):
    """Nested pipeline config."""
    pass


class DeepInner(Config):
    confid = "inner"
    value = Float(1.0, "inner value")


class DeepMiddle(Config, components=[DeepInner], method="nested"):
    confid = "middle"
    y = Float(2.0, "middle y")


class DeepOuter(Config, components=[DeepMiddle], method="nested"):
    confid = "outer"


class MixedCLI(Config, components=[DeepInner], method="nested"):
    confid = "mixedcli"
    top_val = Float(99.0, "flat field on the nested container")


# ---------------------------------------------------------------------------
# add_arguments / from_argparse - flat fields
# ---------------------------------------------------------------------------

class TestArgparseFlat:
    def test_float_field(self):
        cfg = parse(FlatConfig, ["--n-sigma", "3.0"])
        assert cfg.n_sigma == 3.0

    def test_int_field(self):
        cfg = parse(FlatConfig, ["--iterations", "200"])
        assert cfg.iterations == 200

    def test_string_field(self):
        cfg = parse(FlatConfig, ["--label", "my_run"])
        assert cfg.label == "my_run"

    def test_options_field(self):
        cfg = parse(FlatConfig, ["--mode", "thorough"])
        assert cfg.mode == "thorough"

    def test_options_invalid_raises(self):
        parser = argparse.ArgumentParser()
        FlatConfig.add_arguments(parser)
        with pytest.raises(SystemExit):
            parser.parse_args(["--mode", "turbo"])

    def test_bool_flag_true(self):
        cfg = parse(FlatConfig, ["--verbose"])
        assert cfg.verbose is True

    def test_bool_flag_false(self):
        cfg = parse(FlatConfig, ["--no-verbose"])
        assert cfg.verbose is False

    def test_bool_default_unchanged(self):
        cfg = parse(FlatConfig, [])
        assert cfg.verbose is False

    def test_scalar_field(self):
        cfg = parse(FlatConfig, ["--scale", "2.5"])
        assert cfg.scale == 2.5

    def test_seed_int(self):
        cfg = parse(FlatConfig, ["--seed", "42"])
        assert cfg.seed == 42

    def test_seed_none(self):
        cfg = parse(FlatConfig, ["--seed", "none"])
        assert cfg.seed is None

    def test_range_field(self):
        cfg = parse(FlatConfig, ["--bounds", "0.0,5.0"])
        assert cfg.bounds == (0.0, 5.0)

    def test_multioptions_field(self):
        cfg = parse(FlatConfig, ["--steps", "a", "b", "c"])
        assert cfg.steps == {"a", "b", "c"}

    def test_path_field(self):
        cfg = parse(FlatConfig, ["--output", "/tmp/results"])
        assert cfg.output == pathlib.Path("/tmp/results")

    def test_dict_field(self):
        cfg = parse(FlatConfig, ["--meta", '{"key": "val"}'])
        assert cfg.meta == {"key": "val"}

    def test_list_field(self):
        cfg = parse(FlatConfig, ["--tags", "foo", "bar"])
        assert cfg.tags == ["foo", "bar"]

    def test_date_field(self):
        cfg = parse(FlatConfig, ["--start-date", "2025-06-15"])
        assert cfg.start_date == datetime.date(2025, 6, 15)

    def test_time_field(self):
        cfg = parse(FlatConfig, ["--start-time", "14:30:00"])
        assert cfg.start_time == datetime.time(14, 30, 0)

    def test_datetime_field(self):
        cfg = parse(FlatConfig, ["--start-dt", "2025-06-15T14:30:00"])
        assert cfg.start_dt == datetime.datetime(2025, 6, 15, 14, 30, 0)

    def test_static_field_absent_from_parser(self):
        parser = argparse.ArgumentParser()
        FlatConfig.add_arguments(parser)
        # --static-val should not be registered
        with pytest.raises(SystemExit):
            parser.parse_args(["--static-val", "99"])

    def test_unset_field_keeps_default(self):
        cfg = parse(FlatConfig, [])
        assert cfg.n_sigma == 5.0
        assert cfg.mode == "fast"

    def test_multiple_overrides(self):
        cfg = parse(
            FlatConfig, ["--n-sigma", "2.0", "--mode", "balanced", "--verbose"]
        )
        assert cfg.n_sigma == 2.0
        assert cfg.mode == "balanced"
        assert cfg.verbose is True


# ---------------------------------------------------------------------------
# add_arguments / from_argparse - nested configs
# ---------------------------------------------------------------------------

class TestArgparseNested:
    def test_nested_float(self):
        parser = argparse.ArgumentParser()
        PipelineConfig.add_arguments(parser)
        cfg = PipelineConfig.from_argparse(
            parser.parse_args(["--search.n-sigma", "3.0"])
        )
        assert cfg.search.n_sigma == 3.0

    def test_nested_bool_true(self):
        parser = argparse.ArgumentParser()
        PipelineConfig.add_arguments(parser)
        cfg = PipelineConfig.from_argparse(
            parser.parse_args(["--search.verbose"])
        )
        assert cfg.search.verbose is True

    def test_nested_bool_false(self):
        parser = argparse.ArgumentParser()
        PipelineConfig.add_arguments(parser)
        cfg = PipelineConfig.from_argparse(
            parser.parse_args(["--no-search.verbose"])
        )
        assert cfg.search.verbose is False

    def test_nested_path(self):
        parser = argparse.ArgumentParser()
        PipelineConfig.add_arguments(parser)
        cfg = PipelineConfig.from_argparse(
            parser.parse_args(["--output.directory", "/data/out"])
        )
        assert cfg.output.directory == pathlib.Path("/data/out")

    def test_nested_defaults_unchanged(self):
        parser = argparse.ArgumentParser()
        PipelineConfig.add_arguments(parser)
        cfg = PipelineConfig.from_argparse(parser.parse_args([]))
        assert cfg.search.n_sigma == 5.0
        assert cfg.output.compress is False

    def test_nested_multiple_sub_configs(self):
        parser = argparse.ArgumentParser()
        PipelineConfig.add_arguments(parser)
        cfg = PipelineConfig.from_argparse(
            parser.parse_args(
                ["--search.n-sigma", "2.0", "--output.directory", "/tmp"]
            )
        )
        assert cfg.search.n_sigma == 2.0
        assert cfg.output.directory == pathlib.Path("/tmp")



# ---------------------------------------------------------------------------
# Deep (multi-level) nested configs - argparse and click
# ---------------------------------------------------------------------------

class TestDeepNestedCLI:
    def test_argparse_deep_override(self):
        cfg = parse(DeepOuter, ["--middle.inner.value", "9.9"])
        assert cfg.middle.inner.value == 9.9

    def test_argparse_deep_default_unchanged(self):
        cfg = parse(DeepOuter, [])
        assert cfg.middle.inner.value == 1.0

    def test_click_deep_override(self):
        @click.command()
        @DeepOuter.click_options()
        def cmd(**kwargs):
            cfg = DeepOuter.from_click(kwargs)
            click.echo(cfg.middle.inner.value)

        result = CliRunner().invoke(cmd, ["--middle.inner.value", "9.9"])
        assert result.exit_code == 0
        assert "9.9" in result.output

    def test_click_deep_default_unchanged(self):
        @click.command()
        @DeepOuter.click_options()
        def cmd(**kwargs):
            cfg = DeepOuter.from_click(kwargs)
            click.echo(cfg.middle.inner.value)

        result = CliRunner().invoke(cmd, [])
        assert result.exit_code == 0
        assert "1.0" in result.output

    def test_argparse_middle_own_field(self):
        cfg = parse(DeepOuter, ["--middle.y", "7.7"])
        assert cfg.middle.y == 7.7

    def test_click_middle_own_field(self):
        @click.command()
        @DeepOuter.click_options()
        def cmd(**kwargs):
            cfg = DeepOuter.from_click(kwargs)
            click.echo(cfg.middle.y)

        result = CliRunner().invoke(cmd, ["--middle.y", "7.7"])
        assert result.exit_code == 0
        assert "7.7" in result.output


# ---------------------------------------------------------------------------
# Mixed flat+nested CLI
# ---------------------------------------------------------------------------

class TestMixedCLI:
    def test_argparse_flat_field(self):
        cfg = parse(MixedCLI, ["--top-val", "42.0"])
        assert cfg.top_val == 42.0

    def test_argparse_sub_config_field(self):
        cfg = parse(MixedCLI, ["--inner.value", "5.5"])
        assert cfg.inner.value == 5.5

    def test_argparse_both_fields(self):
        cfg = parse(MixedCLI, ["--top-val", "3.0", "--inner.value", "7.0"])
        assert cfg.top_val == 3.0
        assert cfg.inner.value == 7.0

    def test_argparse_defaults_unchanged(self):
        cfg = parse(MixedCLI, [])
        assert cfg.top_val == 99.0
        assert cfg.inner.value == 1.0

    def test_click_flat_field(self):
        @click.command()
        @MixedCLI.click_options()
        def cmd(**kwargs):
            cfg = MixedCLI.from_click(kwargs)
            click.echo(cfg.top_val)

        result = CliRunner().invoke(cmd, ["--top-val", "42.0"])
        assert result.exit_code == 0
        assert "42.0" in result.output

    def test_click_sub_config_field(self):
        @click.command()
        @MixedCLI.click_options()
        def cmd(**kwargs):
            cfg = MixedCLI.from_click(kwargs)
            click.echo(cfg.inner.value)

        result = CliRunner().invoke(cmd, ["--inner.value", "5.5"])
        assert result.exit_code == 0
        assert "5.5" in result.output


# ---------------------------------------------------------------------------
# from_argparse with config file
# ---------------------------------------------------------------------------

class TestFromArgparseFile:
    def test_yaml_file(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("n_sigma: 2.5\nmode: balanced\n")
        cfg = parse(FlatConfig, [str(yaml_file)])
        assert cfg.n_sigma == 2.5
        assert cfg.mode == "balanced"

    def test_toml_file(self, tmp_path):
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('n_sigma = 7.0\nmode = "thorough"\n')
        cfg = parse(FlatConfig, [str(toml_file)])
        assert cfg.n_sigma == 7.0
        assert cfg.mode == "thorough"

    def test_cli_overrides_file(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("n_sigma: 2.5\nmode: balanced\n")
        cfg = parse(FlatConfig, [str(yaml_file), "--n-sigma", "9.9"])
        assert cfg.n_sigma == 9.9
        assert cfg.mode == "balanced"  # file value kept


# ---------------------------------------------------------------------------
# click integration
# ---------------------------------------------------------------------------

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402


class TestClick:
    def test_float_option(self):
        @click.command()
        @FlatConfig.click_options()
        def cmd(**kwargs):
            cfg = FlatConfig.from_click(kwargs)
            click.echo(cfg.n_sigma)

        result = CliRunner().invoke(cmd, ["--n-sigma", "3.0"])
        assert result.exit_code == 0
        assert "3.0" in result.output

    def test_bool_option_true(self):
        @click.command()
        @FlatConfig.click_options()
        def cmd(**kwargs):
            cfg = FlatConfig.from_click(kwargs)
            click.echo(cfg.verbose)

        result = CliRunner().invoke(cmd, ["--verbose"])
        assert result.exit_code == 0
        assert "True" in result.output

    def test_bool_option_false(self):
        @click.command()
        @FlatConfig.click_options()
        def cmd(**kwargs):
            cfg = FlatConfig.from_click(kwargs)
            click.echo(cfg.verbose)

        result = CliRunner().invoke(cmd, ["--no-verbose"])
        assert result.exit_code == 0
        assert "False" in result.output

    def test_options_choice(self):
        @click.command()
        @FlatConfig.click_options()
        def cmd(**kwargs):
            cfg = FlatConfig.from_click(kwargs)
            click.echo(cfg.mode)

        result = CliRunner().invoke(cmd, ["--mode", "thorough"])
        assert result.exit_code == 0
        assert "thorough" in result.output

    def test_nested_float(self):
        @click.command()
        @PipelineConfig.click_options()
        def cmd(**kwargs):
            cfg = PipelineConfig.from_click(kwargs)
            click.echo(cfg.search.n_sigma)

        result = CliRunner().invoke(cmd, ["--search.n-sigma", "3.0"])
        assert result.exit_code == 0
        assert "3.0" in result.output

    def test_nested_bool(self):
        @click.command()
        @PipelineConfig.click_options()
        def cmd(**kwargs):
            cfg = PipelineConfig.from_click(kwargs)
            click.echo(cfg.search.verbose)

        result = CliRunner().invoke(cmd, ["--search.verbose"])
        assert result.exit_code == 0
        assert "True" in result.output

    def test_default_unchanged(self):
        @click.command()
        @FlatConfig.click_options()
        def cmd(**kwargs):
            cfg = FlatConfig.from_click(kwargs)
            click.echo(cfg.n_sigma)

        result = CliRunner().invoke(cmd, [])
        assert result.exit_code == 0
        assert "5.0" in result.output

    def test_multioptions(self):
        @click.command()
        @FlatConfig.click_options()
        def cmd(**kwargs):
            cfg = FlatConfig.from_click(kwargs)
            click.echo(sorted(cfg.steps))

        result = CliRunner().invoke(cmd, ["--steps", "a", "--steps", "b"])
        assert result.exit_code == 0
        assert "a" in result.output
        assert "b" in result.output
