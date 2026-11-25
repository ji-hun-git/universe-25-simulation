"""The command line for everyone (docs/USER_GUIDE.md):

  universe25 colonies                                   the colonies, and how close each comes
  universe25 run   [--colony universe25] [--seed 7000] [--days 1600] [--set k=v ...]
                   [--out DIR] [--plot]                 one run beside Calhoun's record
  universe25 check [--colony universe25] [--seeds 7000-7011] [--workers N] [--days 1600]
                   [--set k=v ...] [--out DIR]          many seeds against the record

Seeds are 7000-9999 (the repo's seed ledger, docs/SEEDS.md).
--set takes dotted config keys, e.g. --set biology.litter_mean=5 --set playground.enabled=false
(the fields: src/universe25/config.py). The research engine with its full logs is the older
form, `universe25 --seed S --out DIR [--config FILE]` (README, "Quick start").
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

COMMANDS = ("colonies", "run", "check")


def parse_set(items: list[str] | None) -> dict:
    """["biology.litter_mean=5", "playground.enabled=false"] -> nested overrides."""
    over: dict = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--set needs key=value, got {item!r}")
        key, val = item.split("=", 1)
        lit = {"true": True, "false": False, "null": None, "none": None}
        v: object
        if val.lower() in lit:
            v = lit[val.lower()]
        else:
            try:
                v = int(val) if val.lstrip("-").isdigit() else float(val)
            except ValueError:
                v = val
        d = over
        keys = key.split(".")
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = v
    return over


def parse_seeds(text: str) -> list[int]:
    """"7000-7011" or "7001,7005" or "7000-7003,7010" -> seeds."""
    seeds: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            seeds += list(range(int(lo), int(hi) + 1))
        else:
            seeds.append(int(part))
    return seeds


def main(argv: list[str]) -> int:
    from universe25.colonies import COLONIES, DEFAULT

    p = argparse.ArgumentParser(prog="universe25", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("colonies", help="the colonies, and how close each comes to the record")
    for name in ("run", "check"):
        s = sub.add_parser(name, help="one run" if name == "run" else "many seeds")
        s.add_argument("--colony", default=DEFAULT, choices=list(COLONIES))
        s.add_argument("--days", type=float, default=1600.0)
        s.add_argument("--set", action="append", metavar="KEY=VALUE",
                       help="a config value over the colony's (repeatable)")
        s.add_argument("--out", help="a folder for the results (JSON, CSV, and a plot)")
        if name == "run":
            s.add_argument("--seed", type=int, default=7000, help="7000-9999")
            s.add_argument("--plot", action="store_true", help="save population.png in --out")
        else:
            s.add_argument("--seeds", default="7000-7011",
                           help="7000-9999, e.g. 7000-7047 (48 seeds, as the repo's validations)")
            s.add_argument("--workers", type=int, default=None)
    a = p.parse_args(argv)

    if a.command == "colonies":
        for name, c in COLONIES.items():
            print(f"{name}{'  (default)' if name == DEFAULT else ''}\n  {c['label']}\n  "
                  f"{c['about']}\n")
        return 0

    import universe25.api as api

    over = parse_set(a.set)
    out = Path(a.out) if a.out else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    if a.command == "run":
        r = api.run(a.colony, a.seed, a.days, over)
        print(r.table())
        if out:
            (out / "run.json").write_text(json.dumps(r.to_dict(), indent=1), encoding="utf-8")
            lines = ["day,n"] + [f"{d},{n}" for d, n in enumerate(r.population, start=1)]
            (out / "population.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
            if a.plot:
                r.plot(out / "population.png")
            print(f"\nwritten to {out}")
        elif a.plot:
            print("\n--plot needs --out")
        return 0

    runs = api.run_many(a.colony, parse_seeds(a.seeds), a.days, over, a.workers)
    check = api.record_check(runs)
    print(check.table())
    if out:
        doc = {**check.to_dict(), "runs": [r.to_dict() for r in runs]}
        (out / "check.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        (out / "check.txt").write_text(check.table() + "\n", encoding="utf-8")
        print(f"\nwritten to {out}")
    return 0
