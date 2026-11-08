#!/usr/bin/env python
"""Run the eval-only Burghardt detectors on the decision traces of a simulator run.

usage: python scripts/detect.py <run_dir> [--surrogates 1000] [--max-individuals 400] [--seed 0]
Reads every trace_*.npz in <run_dir> (written when the run had `trace.windows`), writes
<run_dir>/detectors_unvalidated.json and prints one line per window and episode kind. Outputs
are unvalidated (PHASE4_DESIGN.md section 2); nothing here feeds back into a policy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SHOW = (("n_episodes", "eps", "{:.0f}"), ("nf_index_unvalidated", "nf", "{:.2f}"),
        ("onset_trigger_free_unvalidated", "tf", "{:.2f}"),
        ("seq_struct_reversal_unvalidated", "rev", "{:.2f}"),
        ("rep_rigid_loop_frac_unvalidated", "rigid", "{:.2f}"),
        ("rep_exposure_slope_unvalidated", "slope", "{:+.2f}"),
        ("gate_relaxed_log_ratio_unvalidated", "gate", "{:+.2f}"))


def detect_run(run_dir: Path, surrogates: int, max_individuals: int | None,
               seed: int, self_entries: bool = False) -> dict:
    from universe25.metrics.detectors import detect_trace
    from universe25.metrics.trace import load_trace

    out: dict = {"run_dir": str(run_dir), "surrogates": surrogates,
                 "max_individuals": max_individuals, "windows": {},
                 "rules": "v4_self_entries" if self_entries else "v5"}
    for path in sorted(run_dir.glob("trace_*.npz"),
                       key=lambda p: float(p.stem.split("_")[1])):
        tr = load_trace(path)
        out["windows"][path.stem] = detect_trace(tr, n_surrogates=surrogates, seed=seed,
                                                 max_individuals=max_individuals,
                                                 self_entries=self_entries)
    name = "detectors_v4_unvalidated.json" if self_entries else "detectors_unvalidated.json"
    (run_dir / name).write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    return out


def format_run(out: dict) -> str:
    lines = []
    for w, res in out["windows"].items():
        for kind in ("object", "locomotor"):
            r = res[kind]
            vals = []
            for key, lab, fmt in SHOW:
                v = r.get(key, float("nan"))
                vals.append(f"{lab}={fmt.format(float(v))}")
            fl = "".join("1" if v else "0" for v in r["decisions_unvalidated"].values())
            lines.append(f"{w:16s} {kind:9s} " + " ".join(vals) + f"  flags={fl}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir")
    p.add_argument("--surrogates", type=int, default=1000)
    p.add_argument("--max-individuals", type=int, default=400)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--self-entries", action="store_true",
                   help="v4 trigger set (own cell entries count); diagnostics only")
    a = p.parse_args()
    out = detect_run(Path(a.run_dir), a.surrogates, a.max_individuals or None, a.seed,
                     self_entries=a.self_entries)
    print(format_run(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
