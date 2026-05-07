Defining a config
=================


Subclass :class:`~cfx.Config` and declare fields with a type annotation and
:func:`~cfx.Field`.  Each field carries its default value, validation
constraints, and documentation in one place::

    from cfx import Config, Field
    from typing import Literal

    class ProcessingConfig(Config):
        """Configuration for the main processing pipeline."""
        confid = "processing"

        iterations: int = Field(100, "Number of iterations", ge=1)
        threshold: float = Field(0.5, "Acceptance threshold", ge=0.0, le=1.0)
        label: str = Field("run_01", "Human-readable run label")
        mode: Literal["fast", "balanced", "thorough"] = Field("fast", "Processing mode")
        verbose: bool = Field(False, "Enable verbose logging")

.. testsetup::

    from cfx import Config, Field
    from typing import Literal

    class ProcessingConfig(Config):
        """Configuration for the main processing pipeline."""
        confid = "processing"

        iterations: int = Field(100, "Number of iterations", ge=1)
        threshold: float = Field(0.5, "Acceptance threshold", ge=0.0, le=1.0)
        label: str = Field("run_01", "Human-readable run label")
        mode: Literal["fast", "balanced", "thorough"] = Field("fast", "Processing mode")
        verbose: bool = Field(False, "Enable verbose logging")

``print(cfg)`` renders the full schema as a table - no extra code required:

.. doctest::

    >>> cfg = ProcessingConfig()
    >>> print(cfg)  # doctest: +NORMALIZE_WHITESPACE
    ProcessingConfig: Configuration for the main processing pipeline.
    Config           | Key        | Value  | Description
    -----------------+------------+--------+-------------------------
    ProcessingConfig | iterations | 100    | Number of iterations
    ProcessingConfig | threshold  | 0.5    | Acceptance threshold
    ProcessingConfig | label      | run_01 | Human-readable run label
    ProcessingConfig | mode       | fast   | Processing mode
    ProcessingConfig | verbose    | False  | Enable verbose logging

In a Jupyter notebook the same table is rendered as HTML automatically via
the standard ``_repr_html_`` protocol.

Dot-access and dict-style access are interchangeable.  Both route through
the same field validation:

.. doctest::

    >>> cfg.iterations = 200
    >>> cfg["mode"] = "thorough"

    >>> cfg.threshold = 1.5
    Traceback (most recent call last):
        ...
    ValueError: Expected value <= 1.0, got 1.5

    >>> cfg["mode"] = "turbo"
    Traceback (most recent call last):
        ...
    ValueError: Expected 'turbo' to be one of ('fast', 'balanced', 'thorough')

    >>> cfg["no_such"] = 1
    Traceback (most recent call last):
        ...
    KeyError: 'no_such'

See :doc:`fields` for the full annotation → field type mapping and
:doc:`field-modifiers` for callable defaults, static fields, and environment
variable support.


.. _defining-a-config-inheritance:

Inheritance
-----------

A child class inherits every field from its parent and can add new ones or
change defaults.  Fields from the full MRO are collected automatically::

    from cfx import Config, Field
    from typing import Literal

    class DetailedConfig(ProcessingConfig):
        """Adds output and diagnostics fields to the processing pipeline."""
        confid = "detailed"

        output_dir: str = Field("./results", "Directory for output files")
        max_rows: int = Field(10_000, "Maximum rows per output file", ge=1)

    cfg = DetailedConfig()
    cfg.iterations   # 100 - inherited from ProcessingConfig
    cfg.output_dir   # './results' - new field

A child can also change the **default** of a parent field by re-declaring it::

    class QuietConfig(ProcessingConfig):
        confid = "quiet"
        verbose: bool = Field(True, "Enable verbose logging")  # default changed

    QuietConfig().verbose  # True


Composition
-----------

Multiple configs can be combined into a single parent using ``components=``::

    from cfx import Config, Field

    class FormatConfig(Config):
        """Output formatting settings."""
        confid = "format"
        precision: int = Field(6, "Decimal places in numeric output")
        encoding: str = Field("utf-8", "Output file encoding")

    class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
        """Groups processing and formatting as nested sub-configs."""
        pass

    cfg = PipelineConfig()
    cfg.processing.iterations = 500
    cfg.format.precision = 3

Each sub-config is fully independent — ``cfg.processing`` and ``cfg.format``
are separate objects with their own field values.  See :doc:`composition` for
flat merging, serialization, and all other composition options.
