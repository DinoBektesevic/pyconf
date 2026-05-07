Config composition
==================


.. _composition:

Inheritance
-----------

Standard Python inheritance works naturally.  Fields are collected from the
full MRO automatically, so a child class has all parent fields plus any it
adds or overrides::

    from cfx import Config, Int, Float, Options

    class ProcessingConfig(Config):
        confid = "processing"
        iterations = Int(100, "Number of iterations", ge=1)
        threshold = Float(0.5, "Acceptance threshold", ge=0.0, le=1.0)
        mode = Options(("fast", "balanced", "thorough"), "Processing mode")

    class ChildConfig(ProcessingConfig):
        confid = "child"
        mode = Options(("fast", "balanced", "thorough"), "Processing mode",
                       default_value="balanced")  # changed default
        max_size = Int(1000, "Maximum item count", ge=1)

.. testsetup::

    from cfx import Config, Int, Float, Options, String, Bool

    class ProcessingConfig(Config):
        confid = "processing"
        iterations = Int(100, "Number of iterations", ge=1)
        threshold = Float(0.5, "Acceptance threshold", ge=0.0, le=1.0)
        mode = Options(("fast", "balanced", "thorough"), "Processing mode")

    class ChildConfig(ProcessingConfig):
        confid = "child"
        mode = Options(("fast", "balanced", "thorough"), "Processing mode",
                       default_value="balanced")
        max_size = Int(1000, "Maximum item count", ge=1)

    class FormatConfig(Config):
        confid = "format"
        precision = Int(6, "Decimal precision")
        encoding = String("utf-8", "Output encoding")

    class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
        pass

.. doctest::

    >>> cfg = ChildConfig()
    >>> cfg.iterations
    100
    >>> cfg.mode
    'balanced'
    >>> cfg.max_size
    1000


Composing with ``components=``
------------------------------

Pass a list of config classes as ``components=`` to assemble them into a
larger config::

    from cfx import Config, Int, String

    class FormatConfig(Config):
        confid = "format"
        precision = Int(6, "Decimal precision")
        encoding = String("utf-8", "Output encoding")

    class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
        pass

.. doctest::

    >>> cfg = PipelineConfig()
    >>> cfg.processing.iterations
    100
    >>> cfg.format.precision
    6

Each component becomes a sub-object accessible by its ``confid``.

.. rubric:: The ``confid`` attribute

Every config class has a ``confid`` string identifier.  If you do not set it
explicitly, it defaults to the **lowercase class name**::

    class QuickConfig(Config):
        field1 = Int(1, "A field")

    QuickConfig.confid   # 'quickconfig'

Set ``confid`` explicitly whenever a class will be used as a component, so
the resulting attribute name is predictable::

    class FormatConfig(Config):
        confid = "format"  # accessible as parent_cfg.format
        precision = Int(6, "Decimal precision")

``confid`` becomes the attribute name in nested composition and the key in
nested serialization.


Nested sub-configs
------------------

Each component becomes a fresh sub-object on every parent instance,
accessible as an attribute named after its ``confid``::

    cfg = PipelineConfig()
    cfg.processing.iterations = 200
    cfg.format.precision = 3

    print(cfg.processing)   # full table for ProcessingConfig
    print(cfg.format)       # full table for FormatConfig

Each parent instance gets its own independent sub-configs.  Mutating
``cfg1.processing`` has no effect on ``cfg2.processing``.

``to_dict()`` produces a nested dict keyed by confid; ``from_dict()`` routes
each sub-dict back to its component class::

.. doctest::

    >>> cfg2 = PipelineConfig()
    >>> cfg2.processing.iterations = 200
    >>> cfg2.format.precision = 3
    >>> cfg2.to_dict()  # doctest: +NORMALIZE_WHITESPACE
    {'processing': {'iterations': 200, 'threshold': 0.5, 'mode': 'fast'}, 'format': {'precision': 3, 'encoding': 'utf-8'}}
    >>> cfg3 = PipelineConfig.from_dict(cfg2.to_dict())
    >>> cfg3.processing.iterations
    200

**Duplicate ``confid`` values across components are not allowed.**  If two
classes in the ``components=`` list share a ``confid``, a ``ValueError`` is
raised at class-definition time.

Mixed own fields and components
--------------------------------

A config that uses ``components=`` can also declare its own flat fields
alongside the sub-configs::

    from cfx import String, Bool

    class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
        confid = "pipeline"
        run_id = String("run_01", "Run identifier")
        dry_run = Bool(False, "Validate only; skip writes")

.. doctest::

    >>> from cfx import String, Bool
    >>> class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
    ...     confid = "pipeline"
    ...     run_id = String("run_01", "Run identifier")
    ...     dry_run = Bool(False, "Validate only; skip writes")
    >>> cfg = PipelineConfig()
    >>> cfg.run_id
    'run_01'
    >>> cfg.processing.iterations
    100
    >>> cfg.format.precision
    6

Own fields appear before sub-config fields in the display table.  ``to_dict``
produces a flat key for each own field and a nested sub-dict for each
component::

.. doctest::

    >>> sorted(cfg.to_dict().keys())
    ['dry_run', 'format', 'processing', 'run_id']

For projecting a config tree into a different namespace, or exposing a
curated subset of fields under new names, see :doc:`views`.
