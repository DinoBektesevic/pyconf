<p align="center">
  <img src="https://raw.githubusercontent.com/DinoBektesevic/cfx/main/docs/_static/logo/color_large.svg" alt="cfx" width="300">
</p>

<p align="center">
  <a href="https://github.com/DinoBektesevic/cfx/actions/workflows/ci.yml">
    <img src="https://github.com/DinoBektesevic/cfx/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://cfx.readthedocs.io/en/latest/">
    <img src="https://readthedocs.org/projects/cfx/badge/?version=latest" alt="Docs">
  </a>
  <a href="https://pypi.org/project/cfx/">
    <img src="https://img.shields.io/pypi/v/cfx" alt="PyPI">
  </a>
</p>

# cfx

Declare configuration fields next to the classes that use them. Each field
carries its own default, type checking, and documentation. Compose any set of
configs into a larger one, nested or flat, and get serialization, CLI
integration, and a self-documenting display for free.

```python
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
```

```
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
```

- **Validated fields** — typos and bad values raise immediately at the point of assignment, not silently hours later.
- **Self-documenting** — `print(cfg)` renders a tree of the config hierarchy followed by a unified table of all fields, nested included. In Jupyter the same layout renders as HTML automatically via `_repr_html_`.
- **Composable** — assemble configs from multiple subsystem configs, nested or flat, with serialization, display, and CLI support throughout.
- **Documented** — every field carries a doc string shown alongside its value. In large pipelines the same parameter name (e.g. `kernel_size`) can appear in multiple sub-configs targeting different stages; the doc string and the sub-config namespace keep the purpose clear at each site.
- **Views** — project a config tree into a custom namespace. Expose a curated subset of fields under new names with `ConfigView`, auto-generate prefixed aliases with `AliasedView`, or enforce that two fields always stay in sync with `Mirror`.
- **Serializable** — round-trip to/from dict or YAML with one method call.
- **CLI-ready** — every config exposes `add_arguments` / `from_argparse` for argparse and `click_options` / `from_click` for Click. Nested sub-configs use dot-notation flags (e.g. `--worker.threads`).
- **Extensible** — subclass `ConfigField` to add your own field types with custom validation and normalization.
- **Zero hard dependencies** — YAML and Click support are optional.

## Installation

```bash
pip install cfx
```

With optional backends:

```bash
pip install "cfx[yaml]"   # adds PyYAML
pip install "cfx[click]"  # adds Click
pip install "cfx[all]"    # everything
```

## Quick start

```python
from cfx import Config, Field
from typing import Literal

class ProcessingConfig(Config):
    confid = "processing"
    iterations: int = Field(100, "Number of iterations", minval=1)
    threshold: float = Field(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
    label: str = Field("run_01", "Human-readable run label")
    mode: Literal["fast", "balanced", "thorough"] = Field("fast", "Processing mode")
    verbose: bool = Field(False, "Enable verbose logging")

cfg = ProcessingConfig()

# Dot access and dict-style access are interchangeable
cfg.iterations = 200
cfg["mode"] = "thorough"

# Bad values raise immediately
cfg.threshold = 1.5   # ValueError: Expected value <= 1.0, got 1.5

# Serialize to dict or YAML
d = cfg.to_dict()
cfg2 = ProcessingConfig.from_dict(d)

# Copy with overrides, diff two instances
modified = cfg.copy(iterations=500)
cfg.diff(modified)   # {'iterations': (200, 500)}
```

For field types not expressible via annotations — custom coercion, angular
ranges, unit normalization — subclass `ConfigField` and override `normalize`
and `validate`:

```python
from cfx.types import ConfigField

class Angle(ConfigField):
    def normalize(self, value):
        return float(value) % 360.0   # wrap to [0, 360)

    def validate(self, value):
        if not isinstance(value, float):
            raise TypeError(f"Expected float, got {type(value).__name__!r}")
```

### Views

Project any config tree into a custom namespace — useful when the internal
structure is more complex than what a consumer needs to see:

```python
from cfx import Config, Field, ConfigView, Alias, AliasedView

class ProcessingConfig(Config):
    confid = "processing"
    iterations: int = Field(100, "Number of iterations")
    threshold: float = Field(0.5, "Acceptance threshold")

class FormatConfig(Config):
    confid = "format"
    precision: int = Field(6, "Decimal places")
    encoding: str = Field("utf-8", "Output encoding")

class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
    confid = "pipeline"

# Hand-written curated view
class RunSummary(ConfigView):
    n_iter   = Alias(PipelineConfig.processing.iterations)
    decimals = Alias(PipelineConfig.processing.threshold)

cfg = PipelineConfig()
v = RunSummary(cfg)
v.n_iter    # 100
v.n_iter = 500
cfg.processing.iterations  # 500 — write goes through

# Auto-generated prefixed view (owns its own component instances)
class JobView(AliasedView, components=[ProcessingConfig, FormatConfig]):
    pass

jv = JobView()
jv.processing_iterations = 300
jv.format_precision = 3
```

### Environment variables

Back any field with an environment variable — the value is read lazily, so
the same class works across environments without subclassing:

```python
from cfx import Config, Field

class ServiceConfig(Config):
    host: str = Field("localhost", "Database host", env="DB_HOST")
    port: int = Field(5432, "Port", env="DB_PORT")

# DB_HOST=prod.example.com python run.py
cfg = ServiceConfig()
cfg.host   # 'prod.example.com' — from env, no code change needed
```

### CLI

Every config exposes `add_arguments` / `from_argparse` for argparse and
`click_options` / `from_click` for Click. Nested sub-configs use dot-notation
flags automatically:

```python
import argparse

parser = argparse.ArgumentParser()
ProcessingConfig.add_arguments(parser)
cfg = ProcessingConfig.from_argparse(parser.parse_args())
# python run.py --iterations 200 --mode thorough --no-verbose
```

## License

GPL-3.0-only — see [LICENSE](LICENSE).
