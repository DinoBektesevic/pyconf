cfx
===

.. raw:: html

   <p class="cfx-subtitle">Lightweight self-documenting configuration classes via Python descriptors.</p>

Declare configuration fields next to the classes that use them. Each field
carries its own default, type checking, and documentation. Compose any set of
configs into a larger one, flat or nested, and get serialization, CLI
integration, and a self-documenting display for free::

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

    cfg = PipelineConfig()
    print(cfg)

.. code-block:: text

    PipelineConfig: Image analysis pipeline.
    └─ SourceConfig: Source detection and measurement.
        └─ CalibConfig: Photometric calibration parameters.
    Config         | Key        | Value  | Description
    ---------------+------------+--------+-----------------------------
    PipelineConfig | run_id     | run_01 | Run identifier
    PipelineConfig | dry_run    | False  | Validate only; skip writes
    SourceConfig   | n_sigma    | 3.0    | Detection threshold in sigma
    CalibConfig    | scale      | 1.0    | Flux scale factor
    CalibConfig    | zero_point | 25.0   | Photometric zero-point

.. rubric:: Features

- **Validated fields** - typos and bad values raise immediately at the point
  of assignment, not silently hours later.
- **Self-documenting** - ``print(cfg)`` renders a tree of the config hierarchy
  followed by a unified table of all fields, nested included.  In Jupyter the
  same layout renders as HTML automatically via ``_repr_html_``.
- **Composable** - assemble configs from multiple subsystem configs into a
  nested hierarchy, each sub-config accessible by name. Serialize, display,
  and address from the CLI with consistent dot-notation throughout.
- **Serializable** - round-trip to/from dict, YAML, and TOML with one method
  call.
- **CLI-ready** - every config exposes ``add_arguments`` / ``from_argparse``
  for argparse and ``click_options`` / ``from_click`` for Click.  Nested
  sub-configs use dot-notation flags (e.g. ``--source.n-sigma``).
- **Extensible** - subclass :class:`~cfx.ConfigField` to add your own field
  types with custom validation and normalization.
- **Zero hard dependencies** - YAML, TOML, and Click support are optional.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   defining
   using
   composition
   serialization
   cli
   fields
   sharp-edges
   advanced

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   api/index

.. toctree::
   :maxdepth: 1
   :caption: Development

   changelog
