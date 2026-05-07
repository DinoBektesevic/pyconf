All hand-written RST documentation pages now contain executable ``.. doctest::``
blocks with expected output.  The Sphinx doctest builder (``sphinx-build -b doctest``)
verifies every example on each CI run, keeping the docs in sync with the
implementation.
