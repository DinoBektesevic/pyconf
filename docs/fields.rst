Fields
======

Fields can broadly be categorized into three groups:

1. based on field declaration style,
2. based on field modifiers and
3. as field views

1. Based on field **declaration styles** we have three types of fields:

- **Inferred fields** - the field type is inferred from the type-annotation:
  ``field: int = Field(100, "a field")``
- **Explicit fields** - a concrete ``cfx.types`` used directly:
  ``threshold = Float(0.5, "a field")``
- **Custom fields** - user provided implementation of :class:`~cfx.ConfigField`:
  See :doc:`custom-fields`.

2. Based on field **modifiers** we have:

   - **computed fields** - fields invoking a function to calculate a return value
   - **static fields** - immutable fields set once at definition time
   - **env fields** - fields deriving their value from an environment variable

There is nothing special separating these types. This taxonomy exists purely for
context throughout the text. All of these types of fields share the common
definition and validation pipeline:

.. code-block:: text

    Inferred field -> resolves annotation to -> Explicit field -> subclasses -> ConfigField <- subclassed by <- Custom field

The distinction matters in practice because each style makes a different tradeoff:

- Inferred fields support static type checking, but can not re-define normalization,
  validation, serialization or CLI behaviour.
- Explicit fields can override this behaviour, but can't be statically type-checked.
- Custom fields exist to cover those cases that can not be expressed by modifying
  an explicit type: non-standard coercion, domain-specific validation, custom
  serialization, or bespoke CLI behaviour. See :doc:`custom-fields`.

The third group — field views — are the odd ones out. :class:`~cfx.Alias` and
:class:`~cfx.Mirror` look and behave like fields but are implemented against
:class:`~cfx.Config` or :class:`~cfx.ConfigView` directly. This is completely
transparent to you and their application makes their special nature and function
obvious. See :doc:`views`.

In this and the following sections the details and important information
related to these fields are discussed:

- See :doc:`fields` (this document) for the inferred vs explicit fields
- See :doc:`custom-fields` for details on custom fields
- See :ref:`computed-fields` for details on computed fields (see
  also :doc:`sharp-edges` for edge-cases)
- See :doc:`views` for more details (and :ref:`cross-field-validation`
  for more details on operations over a schema of fields)

.. _explicit-field-types:

Explicit field types
--------------------

These are the concrete types that inferred fields resolve to at class-definition time. Using these
fields directly does not support static type checking — the value type is not visible to the type checker.
Therefore it's more recommended to rely on type
annotated fields described in :ref:`inferred-field-types`.

However, when annotation inference is not enough — custom validation logic,
domain-specific coercion, or constraint combinations not expressible via
annotations - import, inherit, overload etc. and use the concrete field classes
directly::

    from cfx import Config
    from cfx.types import Float, Options, String

    class ProcessingConfig(Config):
        threshold = Float(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
        mode = Options(("fast", "balanced"), "Processing mode")
        label = String("run_01", "Human-readable run label", maxsize=64)

.. note::

   :class:`~cfx.Options` and :class:`~cfx.MultiOptions` have a different
   constructor order: ``(options, doc, default_value=None, ...)`` — the
   allowed choices come first.  When using ``Field()`` this is handled
   automatically.

+------------------------------+------------------------------------------------------------------------+
| Type                         | Description                                                            |
+==============================+========================================================================+
| :class:`~cfx.ConfigField`    | Base class. No validation; accepts any value. Use when you intend to   |
|                              | subclass it (see :doc:`custom-fields`).                                |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Any`            | Explicit escape hatch. No validation; signals to readers that the      |
|                              | absence of constraints is intentional.                                 |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Bool`           | ``True`` or ``False``. Rejects ``int`` — unlike Python's own           |
|                              | truthiness, ``1`` is not a ``bool`` here.                              |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Int`            | Integer. Optional ``minval`` and ``maxval``.                           |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Float`          | Float. Also accepts ``int`` on assignment. Optional ``minval`` and     |
|                              | ``maxval``.                                                            |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Scalar`         | Either ``int`` or ``float``. Use when both are acceptable. Optional    |
|                              | ``minval`` and ``maxval``.                                             |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.String`         | Text string. Optional ``minsize``, ``maxsize``, and ``predicate`` (a   |
|                              | callable that returns ``True`` for valid values).                      |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Options`        | One value from a fixed set. Default is the first option unless         |
|                              | ``default_value`` is supplied.                                         |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.MultiOptions`   | A ``set`` that is a subset of a fixed set of choices.                  |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Path`           | A ``pathlib.Path``. Coerces plain strings on assignment. Optional      |
|                              | ``must_exist=True`` to reject paths that do not exist on disk.         |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Seed`           | An ``int`` or ``None``. ``None`` conventionally means "draw randomly   |
|                              | at runtime".                                                           |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Range`          | A ``(min, max)`` tuple. Validates ``min < max``.                       |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.List`           | A list. Optional ``element_type``, ``minlen``, and ``maxlen``.         |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Dict`           | An untyped dict. Useful for free-form sub-structure that is too loose  |
|                              | to warrant a nested :class:`~cfx.Config`.                              |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Date`           | A ``datetime.date``.                                                   |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.Time`           | A ``datetime.time``.                                                   |
+------------------------------+------------------------------------------------------------------------+
| :class:`~cfx.DateTime`       | A ``datetime.datetime``. Rejects bare ``date`` instances.              |
+------------------------------+------------------------------------------------------------------------+

.. _inferred-field-types:

Inferred fields
---------------

The recommended way to declare config fields is with a type annotation and
:func:`~cfx.Field`::

    from cfx import Config, Field
    from typing import Literal

    class ProcessingConfig(Config):
        confid = "processing"
        iterations: int = Field(100, "Number of iterations", minval=1)
        threshold: float = Field(0.5, "Acceptance threshold", minval=0.0, maxval=1.0)
        label: str = Field("run_01", "Human-readable run label")
        mode: Literal["fast", "balanced", "thorough"] = Field("fast", "Processing mode")
        verbose: bool = Field(False, "Enable verbose logging")

The concrete field type is inferred from the annotation at class-definition
time.  Any constraint keyword accepted by the underlying type can be passed
directly to ``Field()`` (e.g. ``minval=``, ``maxval=``, ``env=``,
``static=``).

Static and runtime validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adding a type annotation enables **static** type checking: mypy, pyright, and
IDEs can verify that only the right type is assigned to the field without
running any code.  All field types — inferred, explicit, and custom — perform
**runtime** validation at every assignment, enforcing constraints such as
``minval=`` or option membership.  Value constraints (e.g. "must be > 0") are
inherently runtime concerns and are not expected to be checked statically.

Explicit field types give dynamic checking but lose the static annotation,
since type checkers see the descriptor rather than the value type.

Mapping to field types
^^^^^^^^^^^^^^^^^^^^^^

At definition time, the type annotation is parsed, alongside any required validation
data, and, under the hood, this lookup mapping is used to construct the matching
explicit field type.

+---------------------------------------+---------------------------+------------------------------------------+
| Annotation                            | Resolved type             | Notes                                    |
+=======================================+===========================+==========================================+
| ``bool``                              | :class:`~cfx.Bool`        |                                          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``int``                               | :class:`~cfx.Int`         | Optional ``minval``, ``maxval``          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``float``                             | :class:`~cfx.Float`       | Optional ``minval``, ``maxval``; also    |
|                                       |                           | accepts ``int``                          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``str``                               | :class:`~cfx.String`      | Optional ``minsize``, ``maxsize``,       |
|                                       |                           | ``predicate``                            |
+---------------------------------------+---------------------------+------------------------------------------+
| ``pathlib.Path``                      | :class:`~cfx.Path`        | Optional ``must_exist=True``             |
+---------------------------------------+---------------------------+------------------------------------------+
| ``Literal["a", "b"]``                 | :class:`~cfx.Options`     | Default must be one of the literals      |
+---------------------------------------+---------------------------+------------------------------------------+
| ``set[Literal["a", "b"]]``            | :class:`~cfx.MultiOptions`|                                          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``list[T]``                           | :class:`~cfx.List`        | Optional ``element_type``, ``minlen``,   |
|                                       |                           | ``maxlen``                               |
+---------------------------------------+---------------------------+------------------------------------------+
| ``tuple[T, T]``                       | :class:`~cfx.Range`       | Validates ``min < max``                  |
+---------------------------------------+---------------------------+------------------------------------------+
| ``int | None``                        | :class:`~cfx.Seed`        | ``None`` means "choose randomly at       |
| ``Optional[int]``                     |                           | runtime"                                 |
+---------------------------------------+---------------------------+------------------------------------------+
| ``int | float``                       | :class:`~cfx.Scalar`      |                                          |
| ``Union[int, float]``                 |                           |                                          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``datetime.date``                     | :class:`~cfx.Date`        |                                          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``datetime.time``                     | :class:`~cfx.Time`        |                                          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``datetime.datetime``                 | :class:`~cfx.DateTime`    | Rejects bare ``date`` instances          |
+---------------------------------------+---------------------------+------------------------------------------+
| ``dict``                              | :class:`~cfx.Dict`        | Untyped free-form dict                   |
+---------------------------------------+---------------------------+------------------------------------------+
| ``typing.Any``                        | :class:`~cfx.Any`         | No validation; signals intentional       |
|                                       |                           | opt-out                                  |
+---------------------------------------+---------------------------+------------------------------------------+
| ``Final[T]``                          | Same as ``T``, static=True| Cannot be set on instances               |
+---------------------------------------+---------------------------+------------------------------------------+
