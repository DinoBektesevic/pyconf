Advanced Usage
==============


This page covers implementation details you will need when writing custom
field types.  For the quick version - a working custom field and callable
defaults - see :ref:`custom-fields` in the User Guide.


Normalizing the descriptor's defaultval
----------------------------------------

When a custom ``__set__`` transforms values (e.g. ``Angle`` wraps degrees to
``[0, 360)``), the transformation runs on every instance assignment but
**not** on the raw ``default_value`` passed to ``ConfigField.__init__``.
``Config.__init__`` seeds each field via ``setattr``, so instances do see the
normalized value.  The descriptor's own ``defaultval`` attribute holds the
original raw value.

This is only a problem if code inspects ``defaultval`` directly (e.g. for
equality tests or documentation generation).  To keep things consistent,
normalize in ``Angle.__init__`` as well::

    from cfx import Config, ConfigField, Float

    class Angle(ConfigField):
        """An angle in degrees, stored normalized to [0, 360)."""

        def __init__(self, default_value, doc, **kwargs):
            if isinstance(default_value, (int, float)):
                default_value = float(default_value) % 360.0
            super().__init__(default_value, doc, **kwargs)

        def validate(self, value):
            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"Angle requires a number, got {type(value).__name__!r}"
                )

        def __set__(self, obj, value):
            if self.static:
                raise AttributeError("Cannot set a static config field.")
            self.validate(value)
            setattr(obj, self.private_name, float(value) % 360.0)


    class SurveyConfig(Config):
        heading = Angle(370.0, "Survey heading in degrees")

    SurveyConfig().heading                       # 10.0
    type(SurveyConfig()).heading.defaultval      # 10.0 - also normalized


How ``__set__`` and ``validate`` interact
-----------------------------------------

The base :meth:`ConfigField.__set__` does three things in order:

1. Checks ``self.static`` and raises ``AttributeError`` if set.
2. Calls ``self.validate(value)`` to check the raw input.
3. Stores the value directly in ``instance.__dict__`` under the private name.

When you override ``__set__`` to normalize a value, you take over the full
storage path.  The recommended pattern is:

1. Guard ``self.static`` yourself - ``super().__set__()`` is no longer called
   so its guard is bypassed.
2. Call ``self.validate(value)`` on the *raw* input before normalizing.
3. Store the *normalized* value via ``setattr(obj, self.private_name, normalized)``.

This avoids double-validation (validate once on raw, store normalized) and
keeps the check and the store close together.  :class:`~cfx.Path` follows
the same pattern - it coerces strings to ``pathlib.Path`` before storing::

    class Angle(ConfigField):
        def __set__(self, obj, value):
            if self.static:                                       # 1. static guard
                raise AttributeError("Cannot set a static config field.")
            self.validate(value)                                  # 2. validate raw
            setattr(obj, self.private_name, float(value) % 360.0)  # 3. store normalized

.. important::

   Any ``__set__`` override that bypasses ``super().__set__()`` **must**
   re-check ``self.static`` itself.  Forgetting this makes the static flag
   silently ineffective for that field type.


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
