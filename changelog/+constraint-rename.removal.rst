Renamed constraint kwargs on numeric and collection field types to match Pydantic v2
naming, which maps directly to JSON Schema keywords.

- ``Int``, ``Float``, ``Scalar``: ``minval=`` → ``ge=``, ``maxval=`` → ``le=``.
  New constraints added: ``gt=`` (strict lower bound), ``lt=`` (strict upper bound),
  ``multiple_of=``.
- ``String``: ``minsize=`` → ``min_length=``, ``maxsize=`` → ``max_length=``.
  New constraint added: ``pattern=`` (regex applied via ``re.fullmatch``).
  ``predicate=`` is kept as a non-schema escape hatch for callable validation.
- ``List``: ``minlen=`` → ``min_length=``, ``maxlen=`` → ``max_length=``.
- ``Dict``: new ``min_length=`` / ``max_length=`` kwargs constraining the number of keys.
- ``DateTime``: new ``tz_aware=`` kwarg; rejects naive datetimes when ``True``.
