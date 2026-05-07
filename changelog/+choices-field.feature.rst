Added ``choices=`` keyword to :func:`~cfx.Field`.  Pass a tuple of allowed
values to get an :class:`~cfx.Options` field (or :class:`~cfx.MultiOptions`
for a ``set``-annotated field) without needing a ``Literal[...]`` annotation —
useful when the set of choices is a runtime constant rather than a literal.
