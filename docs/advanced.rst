Advanced Usage
==============

.. _cross-field-validation:

Cross-field validation
----------------------

Override :meth:`~cfx.Config.validate` on the **Config subclass** (not on
individual fields) to enforce relationships between fields.  ``validate()``
is called automatically after deserialization and after
:meth:`~cfx.Config.update`, and can be called manually at any time::

    from cfx import Config, Field

    class BandConfig(Config):
        low: float = Field(1.0, "Lower frequency bound", minval=0.0)
        high: float = Field(2.0, "Upper frequency bound", minval=0.0)

        def validate(self):
            if self.high <= self.low:
                raise ValueError(
                    f"high ({self.high}) must be greater than low ({self.low})"
                )

    BandConfig.from_dict({"low": 5.0, "high": 1.0})
    # ValueError: high (1.0) must be greater than low (5.0)

HTML rendering
--------------

:meth:`~cfx.Config._repr_html_` is called automatically by Jupyter when a
config instance is the last expression in a cell, producing a ``<pre>`` block
for the hierarchy tree followed by an HTML ``<table>`` with one row per field.

To generate the same HTML fragment programmatically - for embedding in a
custom web UI or notebook template - import :func:`~cfx.display.as_table`
directly::

    from cfx.display import as_table

    html = as_table(cfg, format="html")

The output is a self-contained fragment: a ``<pre>...</pre>`` containing the
config tree followed by a ``<table>...</table>`` with one ``<tr>`` per field.
Field class names and values are wrapped in ``<code>`` tags; description cells
are plain text.

Pass ``table_attrs`` to add a CSS class or ``id`` to the ``<table>`` element,
which lets you target it with custom stylesheet rules::

    html = as_table(cfg, format="html",
        table_attrs={"class": "cfx-table", "id": "pipeline"})
    # -> <pre>...</pre><table class="cfx-table" id="pipeline">...</table>

The lower-level building blocks are also available if you need more control::

    from cfx.display import config_tree, flat_table_rows, make_table

    tree = config_tree(cfg)  # unicode tree string
    rows = flat_table_rows(cfg)  # (class, key, value, doc)
    html = make_table(rows, format="html",
        table_attrs={"class": "cfx-table"})  # <table class="cfx-table">...</table>
    text = make_table(rows, format="text")  # fixed-width terminal table
