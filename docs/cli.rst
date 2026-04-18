CLI integration
===============


Generate command-line interfaces for your config classes
automatically, saving you from writing custom argument parsing code.
cfx generates argparse and Click CLI options directly from your config
classes.  Every non-static field becomes a flag; nested sub-configs use
dot-notation (``--source.n-sigma``).  A config file can be supplied as a
positional argument (argparse) or ``--config-file`` option (Click); CLI
flags override file values.

The examples below use the three-level hierarchy from the front page::

    from cfx import Config, Float, String, Bool

    class CalibConfig(Config):
        """Photometric calibration parameters."""
        confid = "calib"
        scale = Float(1.0, "Flux scale factor")
        zero_point = Float(25.0, "Photometric zero-point")

    class SourceConfig(Config, components=[CalibConfig]):
        """Source detection and measurement."""
        confid = "source"
        n_sigma = Float(3.0, "Detection threshold in sigma")

    class PipelineConfig(Config, components=[SourceConfig]):
        """Image analysis pipeline."""
        confid = "pipeline"
        run_id = String("run_01", "Run identifier")
        dry_run = Bool(False, "Validate only; skip writes")


argparse
--------

Call :meth:`~cfx.Config.add_arguments` on a parser, then
:meth:`~cfx.Config.from_argparse` on the parsed result::

    import argparse

    parser = argparse.ArgumentParser()
    PipelineConfig.add_arguments(parser)
    args = parser.parse_args()
    cfg = PipelineConfig.from_argparse(args)

The flags registered for ``PipelineConfig`` are:

.. code-block:: text

    positional:
      config_file                        Optional YAML or TOML config file.
                                         CLI flags override file values.

    options:
      --run-id RUN_ID                    Run identifier
      --dry-run, --no-dry-run            Validate only; skip writes
      --source.n-sigma SOURCE.N_SIGMA    Detection threshold in sigma
      --source.calib.scale FLOAT         Flux scale factor
      --source.calib.zero-point FLOAT    Photometric zero-point

Rules:

- **Underscore -> hyphen** in the flag name (``n_sigma`` -> ``--source.n-sigma``).
- **Bool** fields use :class:`argparse.BooleanOptionalAction`:
  ``--dry-run`` sets ``True``, ``--no-dry-run`` sets ``False``.
- **Nested sub-configs** are prefixed by their ``confid`` with dot notation.
  Deeper nesting extends the prefix (``--source.calib.zero-point``).
- **config_file** is a positional argument registered once at the top level;
  it is not repeated for nested sub-configs.

The complete Python attribute path maps to the flag name like this:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Python path
     - Flag
   * - ``cfg.run_id``
     - ``--run-id``
   * - ``cfg.source.n_sigma``
     - ``--source.n-sigma``
   * - ``cfg.source.calib.zero_point``
     - ``--source.calib.zero-point``

Pass a config file to load base values, then override with flags::

    cfg = PipelineConfig.from_argparse(
        parser.parse_args(["run.yaml", "--source.n-sigma", "5.0"])
    )
    # cfg.source.n_sigma == 5.0; everything else loaded from run.yaml

Flags that are omitted resolve to ``None`` and leave the loaded or default
value unchanged - they do not reset fields to their class defaults.

.. note::

   The config file format is inferred from the file extension.  Files with
   ``.yaml`` or ``.yml`` extensions are parsed as YAML; everything else is
   parsed as TOML.  Passing a YAML file with a ``.txt`` extension will cause
   a TOML parse error.

When you need to merge several configs into a single shared parser, pass
``prefix=`` explicitly::

    parser = argparse.ArgumentParser()
    SourceConfig.add_arguments(parser, prefix="src")
    FormatConfig.add_arguments(parser, prefix="fmt")
    # registers: --src.n-sigma, --fmt.precision, ...


Click
-----

Stack :meth:`~cfx.Config.click_options` on a ``@click.command()`` and call
:meth:`~cfx.Config.from_click` with the command's ``**kwargs``::

    import click

    @click.command()
    @PipelineConfig.click_options()
    def run(**kwargs):
        cfg = PipelineConfig.from_click(kwargs)
        ...

    if __name__ == "__main__":
        run()

The generated options mirror the argparse flags with two differences:

- A ``--config-file`` option is added at the top level instead of a
  positional argument.
- **Bool** fields use click's ``--flag/--no-flag`` syntax rather than
  :class:`~argparse.BooleanOptionalAction`.

.. code-block:: text

    $ python run.py --help
    Usage: run.py [OPTIONS]

    Options:
      --config-file TEXT               Optional YAML or TOML config file.
      --run-id TEXT                    Run identifier
      --dry-run / --no-dry-run         Validate only; skip writes
      --source.n-sigma FLOAT           Detection threshold in sigma
      --source.calib.scale FLOAT       Flux scale factor
      --source.calib.zero-point FLOAT  Photometric zero-point
      --help                           Show this message and exit.

Click is an **optional dependency**::

    pip install "cfx[click]"
