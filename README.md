<p align="center">
  <img src="docs/_static/logo/color_large.svg" alt="pyconf" width="480">
</p>

# pyconf

Declare configuration fields next to the classes that use them.
Each field carries its own default value, type checking, and documentation.

```python
from pyconf import Config, Float, Int, Options, Bool

class RunConfig(Config):
    """Configuration for a data-processing run."""
    confid = "run"
    iterations = Int(100, "Number of processing iterations", minval=1)
    threshold = Float(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
    mode = Options(("fast", "balanced", "thorough"), "Processing mode")
    verbose = Bool(False, "Enable verbose logging")

cfg = RunConfig()
print(cfg)
```

```
RunConfig:
Configuration for a data-processing run.
Key        | Value | Description
-----------+-------+----------------------------------
iterations | 100   | Number of processing iterations
threshold  | 0.5   | Acceptance threshold
mode       | fast  | Processing mode
verbose    | False | Enable verbose logging
```

## What you get

- **Validated fields** — typos and bad values raise immediately at the point of assignment, not silently hours later.
- **Self-documenting** — `print(cfg)` and Jupyter `repr` show a table of every field with its current value and description.
- **Composable** — assemble configs from multiple subsystem configs, either flat (all fields in one namespace) or nested (sub-objects by name).
- **Serializable** — round-trip to/from dict, YAML, and TOML with one method call.
- **Extensible** — subclass `ConfigField` to add your own field types with custom validation and normalization.
- **Zero hard dependencies** — YAML and TOML support are optional soft dependencies.

## Installation

```bash
pip install pyconf
```

With optional serialization backends:

```bash
pip install "pyconf[yaml]"   # adds PyYAML
pip install "pyconf[toml]"   # adds tomli-w
pip install "pyconf[all]"    # both
```

## Quick start

```python
from pyconf import Config, Int, Float, String, Options, Bool, Path

class ProcessingConfig(Config):
    confid = "processing"
    iterations = Int(100, "Number of iterations", minval=1)
    threshold = Float(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
    label = String("run_01", "Human-readable run label")
    mode = Options(("fast", "balanced", "thorough"), "Processing mode")
    verbose = Bool(False, "Enable verbose logging")

cfg = ProcessingConfig()

# Dot access and dict-style access are interchangeable
cfg.iterations = 200
cfg["mode"] = "thorough"

# Bad values raise immediately
cfg.threshold = 1.5   # ValueError: Expected value <= 1.0, got 1.5

# Serialize to dict, YAML, or TOML
d = cfg.to_dict()
cfg2 = ProcessingConfig.from_dict(d)

# Copy with overrides, diff two instances
modified = cfg.copy(iterations=500)
cfg.diff(modified)   # {'iterations': (200, 500)}
```

### Composition

Combine configs into nested sub-objects or a flat merged namespace:

```python
from pyconf import Config, Int, String

class FormatConfig(Config):
    confid = "format"
    precision = Int(6, "Decimal places in numeric output")
    encoding = String("utf-8", "Output file encoding")

class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
    pass

cfg = PipelineConfig()
cfg.processing.iterations = 500
cfg.format.precision = 3
```

## License

GPL-3.0-only — see [LICENSE](LICENSE).
