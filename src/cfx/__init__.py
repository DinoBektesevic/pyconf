"""cfx - lightweight self-documenting configuration classes.

Declare typed, validated, and documented configuration fields directly
on the class that uses them, using annotations and ``Field()``::

    from cfx import Config, Field
    from typing import Literal

    class SearchConfig(Config):
        \"\"\"Configuration for the main search algorithm.\"\"\"
        confid = "search"

        n_sigma: float = Field(5.0, "Detection threshold", ge=0.0)
        method: Literal["DBSCAN", "RANSAC"] = Field("DBSCAN", "Algorithm")
        debug: bool = Field(False, "Enable verbose debug output")

    cfg = SearchConfig()
    cfg.n_sigma = 3.0        # validated immediately
    cfg["method"] = "RANSAC" # dict-style access also works
    print(cfg)               # tabulated Key / Value / Description table
    d = cfg.to_dict()
    cfg2 = SearchConfig.from_dict(d)

For custom field types with advanced validation, import explicit types::

    from cfx.types import Float, Options, ConfigField
"""

from .config import Config as Config
from .config import FrozenConfigError as FrozenConfigError
from .refs import ComponentRef as ComponentRef
from .refs import FieldRef as FieldRef
from .types import *  # noqa: F401, F403
from .views import AliasedView as AliasedView
from .views import ConfigView as ConfigView
from .views import FlatView as FlatView
