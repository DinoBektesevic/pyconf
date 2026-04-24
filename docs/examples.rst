Examples
========

Runnable examples are in the ``examples/`` directory at the root of the
repository.  Each file is self-contained and can be run directly.


FastAPI integration
-------------------

``examples/fastapi_integration.py``

Shows how to use cfx for application settings alongside a FastAPI app.
cfx handles the settings layer — database connection parameters, feature
flags, env-var overrides, CLI arguments.  pydantic handles request/response
schemas; the two roles don't overlap.

Key patterns shown:

- Environment-variable-backed fields (``env="DB_HOST"``)
- Cross-field validation in ``Config.validate()``
- Nested sub-configs via ``components=[DatabaseConfig, AppSettings]``
- CLI entry point via ``add_arguments`` / ``from_argparse``


ML pipeline with views
-----------------------

``examples/ml_pipeline.py``

Shows composable subsystem configs for an ML training pipeline
(preprocessing, model, training) assembled with ``components=``, plus a
:class:`~cfx.ConfigView` that surfaces the most-tweaked parameters under
short names for interactive use in a Jupyter notebook.

Key patterns shown:

- Multi-component config composition
- ``ConfigView`` with ``Alias`` paths for notebook ergonomics
- Writes through the view go back to the underlying config
- CLI entry point with nested ``--model.learning_rate``-style flags


Custom field types
------------------

``examples/custom_fields.py``

Demonstrates three patterns for custom :class:`~cfx.ConfigField` subclasses:

- ``Angle`` — ``normalize`` wraps any numeric input to ``[0, 360)``
- ``LogScale`` — ``validate`` enforces a log10-space range; extra ``__init__`` args
- ``Percentage`` — ``normalize`` rounds to configurable precision; ``validate``
  checks ``[0, 100]``
