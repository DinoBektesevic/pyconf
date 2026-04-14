pyconf
======

Declare configuration fields next to the classes that use them.
Each field carries its own default value, type checking, and documentation::

    from pyconf import Config, Float, Int, Options, Bool

    class RunConfig(Config):
        """Configuration for a data-processing run."""
        confid     = "run"
        iterations = Int(100,   "Number of processing iterations", minval=1)
        threshold  = Float(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
        mode       = Options(("fast", "balanced", "thorough"), "Processing mode")
        verbose    = Bool(False, "Enable verbose logging")

    cfg = RunConfig()
    print(cfg)

.. code-block:: text

    RunConfig:
    Configuration for a data-processing run.
    Key        | Value   | Description
    -----------+---------+----------------------------------
    iterations | 100     | Number of processing iterations
    threshold  | 0.5     | Acceptance threshold
    mode       | fast    | Processing mode
    verbose    | False   | Enable verbose logging

What you get:

- **Validated fields** — typos and bad values raise immediately at the point
  of assignment, not silently hours later.
- **Self-documenting** — ``print(cfg)`` and Jupyter ``repr`` show a table of
  every field with its current value and description.
- **Composable** — assemble configs from multiple subsystem configs, either
  flat (all fields in one namespace) or nested (sub-objects by name).
- **Serializable** — round-trip to/from dict, YAML, and TOML with one method
  call.
- **Extensible** — subclass :class:`~pyconf.ConfigField` to add your own
  field types with custom validation and normalization.
- **Zero hard dependencies** — YAML and TOML support are optional soft
  dependencies.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   defining
   using
   composition
   serialization
   fields
   sharp-edges
   advanced
   api/index
