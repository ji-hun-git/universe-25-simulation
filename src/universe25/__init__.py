"""Universe 25 (Calhoun 1973) simulation, with an optional playground. No play reward.

Quick use (docs/USER_GUIDE.md):

    import universe25 as u25
    r = u25.run("universe25", seed=7001)
    print(r.table())

Colonies: u25.COLONIES. Many seeds and a check against Calhoun's record: u25.run_many,
u25.record_check.
"""

__version__ = "0.2.0"

from universe25.api import (  # noqa: E402
    BEHAVIOUR,
    CENSUS,
    RECORD,
    RecordCheck,
    Run,
    record_check,
    run,
    run_many,
)
from universe25.colonies import COLONIES, colony_config  # noqa: E402

__all__ = ["BEHAVIOUR", "CENSUS", "COLONIES", "RECORD", "RecordCheck", "Run", "colony_config",
           "record_check", "run", "run_many", "__version__"]
