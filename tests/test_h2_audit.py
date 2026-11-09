"""H2 audits that need no simulation (fast tier, run in CI): no policy or learner imports a
detector, trace or PlayScore module; the detector, trace and synthetic-trace code has no
play-named identifier; the config has no play reward; the observation has no play-named field.
The same checks also run inside the slower files they come from."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "src"))

from test_conservation import test_no_play_reward_in_config  # noqa: E402
from test_detectors import (  # noqa: E402
    test_detector_code_has_no_play_named_identifier,
    test_no_policy_or_learner_imports_a_detector,
)
from test_policy import test_h2_no_play_signal_in_policy_module  # noqa: E402

if __name__ == "__main__":
    test_no_policy_or_learner_imports_a_detector()
    test_detector_code_has_no_play_named_identifier()
    test_no_play_reward_in_config()
    test_h2_no_play_signal_in_policy_module()
    print("test_h2_audit: OK")
