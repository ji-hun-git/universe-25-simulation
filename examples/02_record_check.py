"""Many seeds of one colony against Calhoun's record: how many of the record's 14 population
and timeline numbers fall inside the runs' 5-95 % range, and how many runs show the arc.

    python examples/02_record_check.py [colony] [n_seeds]

12 seeds take a few minutes on a multi-core machine. The repo's own validations use 48.
"""
import sys

import universe25 as u25

if __name__ == "__main__":  # needed on Windows: run_many starts worker processes
    colony = sys.argv[1] if len(sys.argv) > 1 else "universe25"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    runs = u25.run_many(colony, seeds=range(7000, 7000 + n))
    print(u25.record_check(runs).table())
