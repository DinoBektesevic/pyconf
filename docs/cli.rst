CLI integration
===============


Generate command-line interfaces for your config classes
automatically, saving you from writing custom argument parsing code.
cfx generates argparse and Click CLI options directly from your config
classes.  Every non-static field becomes a flag; nested sub-configs use
dot-notation (``--worker.threads``).  A config file can be supplied as a
positional argument (argparse) or ``--config-file`` option (Click); CLI
flags override file values.

The examples below use the three-level hierarchy from the front page::

    from cfx import Config, Float, Int, String, Bool

    class FormatConfig(Config):
        """Output formatting."""
        confid = "format"
        precision = Int(6, "Decimal places")
        encoding = String("utf-8", "Output encoding")

    class WorkerConfig(Config, components=[FormatConfig]):
        """Worker settings."""
        confid = "worker"
        threads = Int(4, "Worker threads", minval=1)
        timeout = Float(30.0, "Request timeout in seconds", minval=0.0)

    class AppConfig(Config, components=[WorkerConfig]):
        """Application configuration."""
        confid = "app"
        name = String("myapp", "Application name")
        debug = Bool(False, "Enable debug output")


argparse
--------

Call :meth:`~cfx.Config.add_arguments` on a parser, then
:meth:`~cfx.Config.from_argparse` on the parsed result::

    import argparse

    parser = argparse.ArgumentParser()
    AppConfig.add_arguments(parser)
    args = parser.parse_args()
    cfg = AppConfig.from_argparse(args)

The flags registered for ``AppConfig`` are:

.. code-block:: text

    positional:
      config_file                                      Optional YAML config file.
                                                       CLI flags override file values.

    options:
      --name NAME                                      Application name
      --debug, --no-debug                              Enable debug output
      --worker.threads WORKER.THREADS                  Worker threads
      --worker.timeout WORKER.TIMEOUT                  Request timeout in seconds
      --worker.format.precision WORKER.FORMAT.PRECISION  Decimal places
      --worker.format.encoding WORKER.FORMAT.ENCODING    Output encoding

Rules:

- **Underscore -> hyphen** in the flag name (``run_id`` -> ``--run-id``).
- **Bool** fields use :class:`argparse.BooleanOptionalAction`:
  ``--debug`` sets ``True``, ``--no-debug`` sets ``False``.
- **Nested sub-configs** are prefixed by their ``confid`` with dot notation.
  Deeper nesting extends the prefix (``--worker.format.precision``).
- **config_file** is a positional argument registered once at the top level;
  it is not repeated for nested sub-configs.

The complete Python attribute path maps to the flag name like this:

+----------------------------------+-------------------------------+
| Python path                      | Flag                          |
+==================================+===============================+
| ``cfg.name``                     | ``--name``                    |
+----------------------------------+-------------------------------+
| ``cfg.worker.threads``           | ``--worker.threads``          |
+----------------------------------+-------------------------------+
| ``cfg.worker.format.precision``  | ``--worker.format.precision`` |
+----------------------------------+-------------------------------+

Pass a config file to load base values, then override with flags::

    cfg = AppConfig.from_argparse(
        parser.parse_args(["app.yaml", "--worker.threads", "8"])
    )
    # cfg.worker.threads == 8; everything else loaded from app.yaml

Flags that are omitted resolve to ``None`` and leave the loaded or default
value unchanged — they do not reset fields to their class defaults.

.. note::

   Only ``.yaml`` and ``.yml`` extensions are supported.  Passing a file
   with any other extension will fail at parse time.

When you need to merge several configs into a single shared parser, pass
``prefix=`` explicitly::

    parser = argparse.ArgumentParser()
    ProcessingConfig.add_arguments(parser, prefix="proc")
    FormatConfig.add_arguments(parser, prefix="fmt")
    # registers: --proc.iterations, --fmt.precision, ...


Click
-----

Stack :meth:`~cfx.Config.click_options` on a ``@click.command()`` and call
:meth:`~cfx.Config.from_click` with the command's ``**kwargs``::

    import click

    @click.command()
    @AppConfig.click_options()
    def run(**kwargs):
        cfg = AppConfig.from_click(kwargs)
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
      --config-file TEXT                         Optional YAML config file.
      --name TEXT                                Application name
      --debug / --no-debug                       Enable debug output
      --worker.threads INTEGER                   Worker threads
      --worker.timeout FLOAT                     Request timeout in seconds
      --worker.format.precision INTEGER          Decimal places
      --worker.format.encoding TEXT              Output encoding
      --help                                     Show this message and exit.

Click is an **optional dependency**::

    pip install "cfx[click]"
