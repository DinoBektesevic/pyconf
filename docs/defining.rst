Defining a config
=================

.. contents:: On this page
   :local:
   :depth: 2

Subclass :class:`~pyconf.Config` and declare field descriptors as class
attributes.  Each field carries its default value, type, validation
constraints, and documentation in one place::

    from pyconf import Config, Float, Int, String, Options, Bool

    class ProcessingConfig(Config):
        """Configuration for the main processing pipeline."""
        confid = "processing"

        iterations = Int(100, "Number of iterations", minval=1)
        threshold = Float(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
        label = String("run_01", "Human-readable run label")
        mode = Options(("fast", "balanced", "thorough"), "Processing mode")
        verbose = Bool(False, "Enable verbose logging")

``print(cfg)`` renders the full schema as a table — no extra code required::

    cfg = ProcessingConfig()
    print(cfg)

.. code-block:: text

    ProcessingConfig:
    Configuration for the main processing pipeline.
    Key        | Value   | Description
    -----------+---------+-------------------------------
    iterations | 100     | Number of iterations
    threshold  | 0.5     | Acceptance threshold
    label      | run_01  | Human-readable run label
    mode       | fast    | Processing mode
    verbose    | False   | Enable verbose logging

In a Jupyter notebook the same table is rendered as HTML automatically via
the standard ``_repr_html_`` protocol.

Dot-access and dict-style access are interchangeable.  Both route through
the same field validation::

    cfg.iterations = 200  # dot-access
    cfg["mode"] = "thorough"  # dict-style

    cfg.threshold = 1.5  # ValueError: Expected value <= 1.0, got 1.5
    cfg["mode"] = "turbo"  # ValueError: Expected 'turbo' to be one of ...
    cfg["no_such"] = 1  # KeyError: 'no_such'


.. _defining-a-config-inheritance:

Inheritance
-----------

A child class inherits every field from its parent and can add new ones or
change defaults.  Fields from the full MRO are collected automatically::

    from pyconf import Config, Int, Float, Path, MultiOptions

    class DetailedConfig(ProcessingConfig):
        """Adds output and diagnostics fields to the processing pipeline."""
        confid = "detailed"

        output_dir = Path("./results", "Directory for output files")
        max_rows = Int(10_000, "Maximum rows per output file", minval=1)
        tags = MultiOptions(
            ("debug", "profile", "audit"),
            "Diagnostic tags to enable",
            default_value=set(),
        )

    cfg = DetailedConfig()
    cfg.iterations  # 100 — inherited from ProcessingConfig
    cfg.output_dir  # PosixPath('results') — new field; string coerced to Path
    cfg.tags  # set() — new field with an empty-set default

A child can also change the **default** of a parent field by re-declaring it::

    class QuietConfig(ProcessingConfig):
        confid = "quiet"
        verbose = Bool(True, "Enable verbose logging")  # default changed to True

    QuietConfig().verbose  # True


Composition
-----------

Multiple configs can be combined into a single parent — either as
**nested sub-objects** (the default) or **flat-merged** into one namespace.
The short form is just one line::

    from pyconf import Config, Int, String

    class FormatConfig(Config):
        """Output formatting settings."""
        confid = "format"
        precision = Int(6, "Decimal places in numeric output")
        encoding = String("utf-8", "Output file encoding")

    class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
        """Groups processing and formatting as nested sub-configs."""
        pass

    cfg = PipelineConfig()
    cfg.processing.iterations = 500
    cfg.format.precision = 3

Each sub-config is fully independent — ``cfg.processing`` and ``cfg.format``
are separate objects with their own field values.  See :doc:`composition` for
flat merging, serialization, and all other composition options.
