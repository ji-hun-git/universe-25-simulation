"""The colonies anyone can run, by name (docs/USER_GUIDE.md; the app's presets).

A colony is a YAML config in the repo's `configs/` and, optionally, a fitted member whose
parameters it takes (a JSON file with "members", the first of which is used). Each says, in
`about`, how close it comes to Calhoun's record, misses included. The first is the default.

The package runs from a clone of the repo (`pip install -e .`): the configs are read from the
repo, not from the installed package.
"""
from __future__ import annotations

import json
from pathlib import Path

COLONIES = {
    "universe25": {"label": "Universe 25: Calhoun's pen (final replica)",
                   "config": "configs/replica_v2.yaml", "member": "configs/replica_v2_final.json",
                   # NOTES 2026-11-19: the record fits (U-1, U-3) failed; this member stays.
                   # Seeds 9112-9159, adults counted as Calhoun did (131 days or older).
                   "about": "Calhoun's pen without the playground, as fitted in replica v2. On 48 "
                            "fresh seeds it grows and collapses in 46 runs, and 11 of the "
                            "record's 14 population and timeline numbers fall inside its 5-95 % "
                            "range (9 on an earlier set of 48 seeds). Misses: the peak (2,490; "
                            "record 2,200), N on day 960 (1,320; 1,650) and the last conception "
                            "(day 1,096; 920). Adults are counted as Calhoun counted them, from "
                            "131 days old. Its behaviour is not Calhoun's: few withdrawn mice "
                            "and no beautiful ones."},
    "reference": {"label": "Reference colony (phase 2m, simplified pen)",
                  "config": "configs/default.yaml",
                  "about": "The research colony: Calhoun's sizes in a simplified pen (a 4 x 4 "
                           "grid, nests as points, and a playground he never had). Its population "
                           "curve was fitted to the record: 11 of 15 values inside on 48 seeds. "
                           "It starts late and then grows too fast, so on day 315 it has few "
                           "adults as Calhoun counted them (131 days or older)."},
    "replica": {"label": "Calhoun's pen, unfitted (replica v2 M1-M4)",
                "config": "configs/replica_v2.yaml",
                "about": "Calhoun's own pen with replica v2's settings before any fit (M1-M4)."},
    "scarce": {"label": "Scarce arm (research)", "config": "configs/scarce.yaml",
               "about": "Phase 4's scarce arm: the research colony with food for 1,000 a day."},
}
DEFAULT = next(iter(COLONIES))


def repo_root() -> Path:
    """The clone this package runs from: the folder holding configs/ and scripts/."""
    for p in Path(__file__).resolve().parents:
        if (p / "configs" / "default.yaml").is_file() and (p / "scripts").is_dir():
            return p
    raise RuntimeError("universe25: the repo's configs/ were not found next to the package. "
                       "Install from a clone of the repo: pip install -e .")


def deep_merge(base: dict, over: dict) -> dict:
    """`over` merged into `base`, nested dicts merged key by key."""
    out = dict(base)
    for k, v in over.items():
        nested = isinstance(v, dict) and isinstance(out.get(k), dict)
        out[k] = deep_merge(out[k], v) if nested else v
    return out


def colony(name: str) -> dict:
    if name not in COLONIES:
        raise KeyError(f"unknown colony {name!r}; choose one of {', '.join(COLONIES)}")
    return COLONIES[name]


def colony_overrides(name: str, overrides: dict | None = None) -> tuple[str, dict]:
    """(the colony's YAML path relative to the repo, its member's parameters + `overrides`)."""
    c = colony(name)
    over: dict = {}
    if c.get("member"):
        doc = json.loads((repo_root() / c["member"]).read_text(encoding="utf-8"))
        over = dict(doc["members"][0]["params"])
    return c["config"], deep_merge(over, overrides or {})


def colony_config(name: str, overrides: dict | None = None):
    """The validated Config a colony runs: its YAML, its member's parameters, then `overrides`."""
    from universe25.config import load_config

    path, over = colony_overrides(name, overrides)
    return load_config(repo_root() / path, over)
