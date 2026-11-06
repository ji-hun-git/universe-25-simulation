"""python -m universe25 entry."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running without install
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Universe 25 simulation (no play reward)")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=str, required=True)
    p.add_argument("--config", type=str, default=None)
    p.add_argument("--days", type=float, default=None)
    p.add_argument("--backend", type=str, default=None, choices=["auto", "numpy", "torch", "warp"])
    p.add_argument("--device", type=str, default=None, choices=["auto", "cpu", "cuda"])
    p.add_argument("--playground", type=str, default=None, choices=["on", "off"])
    p.add_argument("--max-agents", type=int, default=None)
    p.add_argument("--policy", type=str, default=None,
                   choices=["need_driven", "mlp_frozen", "mlp_ppo"])
    p.add_argument("--policy-weights", type=str, default=None, help=".npz for mlp kinds")
    p.add_argument("--free-substeps", type=int, default=None,
                   help="free-time sub-steps per decision (P4-8; 1 = off)")
    p.add_argument("--trace-windows", type=str, default=None,
                   help="decision-trace day windows, e.g. 150:170,400:420 (eval-only)")
    args = p.parse_args(argv)

    from universe25.config import load_config
    from universe25.sim import Universe25Sim
    from universe25.metrics.calibration import write_calibration

    overrides: dict = {"seed": args.seed}
    if args.days is not None:
        overrides["days"] = args.days
    if args.backend is not None:
        overrides["backend"] = args.backend
    if args.device is not None:
        overrides["device"] = args.device
    if args.max_agents is not None:
        overrides["max_agents"] = args.max_agents
    if args.policy is not None or args.policy_weights is not None:
        pol: dict = {}
        if args.policy is not None:
            pol["kind"] = args.policy
        if args.policy_weights is not None:
            pol["weights"] = args.policy_weights
        overrides["policy"] = pol
    if args.free_substeps is not None:
        overrides["free_substeps"] = args.free_substeps
    if args.trace_windows:
        wins = [tuple(float(v) for v in w.split(":")) for w in args.trace_windows.split(",")]
        overrides["trace"] = {"windows": wins}
    if args.playground == "on":
        overrides["playground"] = {"enabled": True}
    elif args.playground == "off":
        overrides["playground"] = {"enabled": False}

    cfg_path = args.config
    if cfg_path is None:
        cand = _ROOT / "configs" / "default.yaml"
        cfg_path = str(cand) if cand.is_file() else None

    cfg = load_config(cfg_path, overrides)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(cfg.model_dump_json(indent=2), encoding="utf-8")

    sim = Universe25Sim(cfg, out)
    summary = sim.run()
    cal = write_calibration(out / "metrics.parquet", out / "calibration.json", summary)
    print(json.dumps({"summary": summary, "calibration_mean_rel_error": cal.get("mean_rel_error")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
