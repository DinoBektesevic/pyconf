Views
=====

A *view* projects a config tree into a different namespace — exposing a
curated subset of fields under new names, auto-generating aliases for every
field in a group of configs, or enforcing that two config fields always hold
the same value.

Views are useful when:

- the internal config structure (e.g. deeply nested sub-configs) is more
  complex than what a consumer needs to see;
- the same underlying fields must appear under different names in different
  contexts;
- two separate config fields must always stay in sync.

The examples on this page use these shared config classes::

    from cfx import Config, Float, Int, String, Bool

    class ProcessingConfig(Config):
        confid = "processing"
        iterations = Int(100, "Number of iterations", minval=1)
        threshold = Float(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
        verbose = Bool(False, "Enable verbose logging")

    class FormatConfig(Config):
        confid = "format"
        precision = Int(6, "Decimal places in numeric output")
        encoding = String("utf-8", "Output file encoding")

    class PipelineConfig(Config, components=[ProcessingConfig, FormatConfig]):
        confid = "pipeline"
        run_id = String("run_01", "Run identifier")
        dry_run = Bool(False, "Validate only; skip writes")


ConfigView and Alias
--------------------

:class:`~cfx.ConfigView` is the base class for hand-written projections.
Subclass it and declare :class:`~cfx.Alias` descriptors to expose selected
fields under whatever names suit the consumer::

    from cfx import ConfigView, Alias

    class RunSummary(ConfigView):
        n_iter   = Alias(PipelineConfig.processing.iterations)
        decimals = Alias(PipelineConfig.processing.threshold)
        label    = Alias(PipelineConfig.run_id)

Bind a view to an existing config instance at construction.  All reads and
writes delegate through to the underlying config — the view carries no data
of its own::

    cfg = PipelineConfig()
    cfg.processing.iterations = 250

    v = RunSummary(cfg)
    v.n_iter    # 250 - reads cfg.processing.iterations
    v.decimals  # 0.5 - reads cfg.processing.threshold

    v.n_iter = 500
    cfg.processing.iterations  # 500 - write went through

The ``Alias`` argument is a :class:`~cfx.refs.FieldRef` obtained by
class-level attribute access on a :class:`~cfx.Config`.  Plain dotpath
strings are also accepted (``Alias("processing.iterations")``), but the
object-reference form keeps the path refactorable via IDE rename and
go-to-definition.

A view can span multiple sub-configs by binding to a common parent::

    class RunSummary(ConfigView):
        n_iter    = Alias(PipelineConfig.processing.iterations)
        decimals  = Alias(PipelineConfig.processing.threshold)
        precision = Alias(PipelineConfig.format.precision)

    cfg = PipelineConfig()
    v = RunSummary(cfg)
    v.n_iter     # cfg.processing.iterations
    v.precision  # cfg.format.precision

.. rubric:: Serialization

:meth:`~cfx.ConfigView.to_dict` returns the aliased fields and their current
values::

    v.to_dict()   # {'n_iter': 500, 'decimals': 0.5, 'precision': 6}

:meth:`~cfx.ConfigView.from_dict` applies values from a dict through the
view's aliases and returns a bound view::

    v2 = RunSummary.from_dict({"n_iter": 100, "decimals": 0.3}, cfg)
    cfg.processing.iterations  # 100
    cfg.processing.threshold   # 0.3

Unknown keys in the dict are silently ignored.

.. rubric:: Display

``repr(view)`` shows the class name and current alias values.
``ViewClass._repr_html_()`` (called on the class, not an instance) renders
an HTML table mapping alias names to their dotpaths — useful for inspecting
a view's schema in a Jupyter notebook.


AliasedView
-----------

:class:`~cfx.AliasedView` auto-generates :class:`~cfx.Alias` descriptors for
every field in each declared component.  Unlike :class:`~cfx.ConfigView`, an
``AliasedView`` owns its component instances — construction takes no
arguments::

    from cfx import AliasedView

    class JobView(AliasedView, components=[ProcessingConfig, FormatConfig]):
        pass

    v = JobView()
    v.processing_iterations  # 100 - alias generated as "{confid}_{field}"
    v.format_precision       # 6

    v.processing_iterations = 300
    v.processing.iterations  # 300 - write went through to the component

By default each alias is prefixed with the component's ``confid``, so fields
from different components never conflict.

.. rubric:: Custom prefixes

Pass ``aliases=`` to override the prefix for each component::

    class JobView(AliasedView,
                  components=[ProcessingConfig, FormatConfig],
                  aliases=["proc", "fmt"]):
        pass

    v = JobView()
    v.proc_iterations   # 100
    v.fmt_precision     # 6

Pass ``None`` as a prefix to expose that component's fields without any
prefix::

    class JobView(AliasedView,
                  components=[ProcessingConfig],
                  aliases=[None]):
        pass

    v = JobView()
    v.iterations   # 100 - no prefix

A ``ValueError`` is raised at class-definition time if two auto-generated
aliases collide — whether from the same prefix or from two ``None``-prefix
components with a shared field name::

    class StorageConfig(Config):
        confid = "storage"
        encoding = String("utf-8", "Storage encoding")   # same name as FormatConfig.encoding

    class BadView(AliasedView,
                  components=[FormatConfig, StorageConfig],
                  aliases=[None, None]):
        pass
    # ValueError: Name conflict 'encoding' among auto-generated aliases ...

.. rubric:: Serialization

``to_dict()`` and ``from_dict()`` work the same as for
:class:`~cfx.ConfigView`, except ``from_dict`` takes only the dict argument
(no separate config) and constructs a fresh view::

    v = JobView()
    v.to_dict()   # {'processing_iterations': 100, 'processing_threshold': 0.5, ...}

    v2 = JobView.from_dict({"processing_iterations": 200})
    v2.processing.iterations  # 200


FlatView
--------

:class:`~cfx.FlatView` is an :class:`~cfx.AliasedView` with all prefixes
implicitly ``None`` — every component field is exposed directly by its own
name::

    from cfx import FlatView

    class FlatWorker(FlatView, components=[ProcessingConfig]):
        pass

    w = FlatWorker()
    w.iterations = 200
    w.verbose = True
    w.processing.iterations  # 200

If two components in a ``FlatView`` share a field name, a ``ValueError`` is
raised at class-definition time::

    class ExtraConfig(Config):
        confid = "extra"
        iterations = Int(0, "Also has iterations")

    class BadFlat(FlatView, components=[ProcessingConfig, ExtraConfig]):
        pass
    # ValueError: Name conflict 'iterations' among auto-generated aliases ...

Use :class:`~cfx.AliasedView` with explicit prefixes to resolve the conflict.


Mirror
------

:class:`~cfx.Mirror` is a :class:`~cfx.Config` field descriptor (not a view)
that keeps two or more dotpaths in sync.  A write fans out to every path; a
read asserts that all paths agree and returns the shared value::

    from cfx import Mirror

    class SyncedConfig(Config, components=[ProcessingConfig, FormatConfig]):
        confid = "synced"
        detail = Mirror("processing.iterations", "format.precision")

    cfg = SyncedConfig()
    cfg.detail = 8
    cfg.processing.iterations  # 8
    cfg.format.precision       # 8

    cfg.detail   # 8 - paths agree

If the paths diverge (e.g. one is set independently), reading the mirror
raises ``ValueError``::

    cfg.processing.iterations = 10
    cfg.detail   # ValueError: Mirror 'detail' paths disagree: ...

.. note::

   Unlike :class:`~cfx.Alias` (which walks from ``_alias_root``),
   :class:`~cfx.Mirror` walks from the config instance it is declared on.
   Paths must be relative to that config, not to any component class.
   Use dotpath strings (``"processing.iterations"``) rather than bare
   ``FieldRef`` objects (``ProcessingConfig.iterations``) — the latter
   would produce path ``"iterations"`` which does not reach the component
   field on the parent config.
