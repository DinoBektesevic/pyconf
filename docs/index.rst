cfx
===

.. raw:: html

   <p class="cfx-subtitle">Lightweight self-documenting configuration classes via Python descriptors.</p>

Declare configuration fields next to the classes that use them. Each field
carries its own default, type checking, and documentation. Compose any set of
configs into a larger one, nested or flat, and get serialization, CLI
integration, and a self-documenting display for free::

    from cfx import Config, Field

    class FormatConfig(Config):
        """Output formatting."""
        confid = "format"
        precision: int = Field(6, "Decimal places")
        encoding: str = Field("utf-8", "Output encoding")

    class WorkerConfig(Config, components=[FormatConfig]):
        """Worker settings."""
        confid = "worker"
        threads: int = Field(4, "Worker threads", minval=1)
        timeout: float = Field(30.0, "Request timeout in seconds", minval=0.0)

    class AppConfig(Config, components=[WorkerConfig]):
        """Application configuration."""
        confid = "app"
        name: str = Field("myapp", "Application name")
        debug: bool = Field(False, "Enable debug output")

    cfg = AppConfig()
    print(cfg)

.. code-block:: text

    AppConfig: Application configuration.
    └─ WorkerConfig: Worker settings.
        └─ FormatConfig: Output formatting.
    Config       | Key       | Value | Description
    -------------+-----------+-------+---------------------------
    AppConfig    | name      | myapp | Application name
    AppConfig    | debug     | False | Enable debug output
    WorkerConfig | threads   | 4     | Worker threads
    WorkerConfig | timeout   | 30.0  | Request timeout in seconds
    FormatConfig | precision | 6     | Decimal places
    FormatConfig | encoding  | utf-8 | Output encoding

.. rubric:: Features

- **Validated fields** — typos and bad values raise immediately at the point
  of assignment, not silently hours later.
- **Self-documenting** — ``print(cfg)`` renders a tree of the config hierarchy
  followed by a unified table of all fields, nested included.  In Jupyter the
  same layout renders as HTML automatically via ``_repr_html_``.
- **Composable** — assemble configs from multiple subsystem configs into a
  nested hierarchy, each sub-config accessible by name. Serialize, display,
  and address from the CLI with consistent dot-notation throughout.
- **Documented** — every field carries a doc string shown alongside its value.
  In large pipelines the same parameter name (e.g. ``kernel_size``) can appear
  in multiple sub-configs targeting different stages; the doc string and the
  sub-config namespace keep the purpose clear at each site.
- **Views** — project any config tree into a custom namespace.  Expose a
  curated subset of fields under new names with :class:`~cfx.ConfigView`,
  auto-generate prefixed aliases with :class:`~cfx.AliasedView`, or keep two
  fields in sync with :class:`~cfx.Mirror`.
- **Serializable** — round-trip to/from dict or YAML with one method call.
- **CLI-ready** — every config exposes ``add_arguments`` / ``from_argparse``
  for argparse and ``click_options`` / ``from_click`` for Click.  Nested
  sub-configs use dot-notation flags (e.g. ``--worker.threads``).
- **Extensible** — subclass :class:`~cfx.ConfigField` to add your own field
  types with custom validation and normalization.
- **Zero hard dependencies** — YAML and Click support are optional.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   defining
   using
   composition
   views
   fields
   field-modifiers
   custom-fields
   serialization
   cli
   sharp-edges
   advanced
   examples

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   api/index

.. toctree::
   :maxdepth: 1
   :caption: Development

   changelog
