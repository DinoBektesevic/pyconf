"""cfx - lightweight self-documenting configuration classes.

Declare typed, validated, and documented configuration fields directly
on the class that uses them, using Python descriptors::

    from cfx import Config, Float, Options, Bool

    class SearchConfig(Config):
        \"\"\"Configuration for the main search algorithm.\"\"\"
        confid = "search"

        n_sigma = Float(5.0, "Detection threshold in sigma units", minval=0.0)
        method  = Options(("DBSCAN", "RANSAC"), "Clustering algorithm")
        debug   = Bool(False, "Enable verbose debug output")

    cfg = SearchConfig()
    cfg.n_sigma = 3.0        # validated immediately
    cfg["method"] = "RANSAC" # dict-style access also works
    print(cfg)               # tabulated Key / Value / Description table
    d = cfg.to_dict()
    cfg2 = SearchConfig.from_dict(d)
"""

from .config_field import *  # noqa: F401, F403
from .config import *  # noqa: F401, F403
from .types import *  # noqa: F401, F403
