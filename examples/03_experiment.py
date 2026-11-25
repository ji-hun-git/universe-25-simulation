"""An experiment: what if litters were smaller? The colony as fitted against the same colony
with litter_mean one pup lower, six seeds each, and the population medians plotted.

    python examples/03_experiment.py

Any config value can be changed the same way (the fields: src/universe25/config.py).
Writes examples_out/experiment.png.
"""
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

import universe25 as u25

if __name__ == "__main__":
    seeds = range(7100, 7106)
    base = u25.colony_config("universe25").biology.litter_mean  # the fitted value, 4.9
    arms = {f"as fitted (litter_mean {base:.1f})": None,
            f"smaller litters ({base - 1:.1f})": {"biology": {"litter_mean": base - 1.0}}}
    fig = Figure(figsize=(8, 4.5))
    ax = fig.subplots()
    for (label, over), color in zip(arms.items(), ("#1A1A1A", "#2F5D50")):
        runs = u25.run_many("universe25", seeds=seeds, overrides=over)
        n = min(r.population.size for r in runs)
        pop = np.stack([r.population[:n] for r in runs])
        ax.plot(np.arange(1, n + 1), np.median(pop, axis=0), color=color, label=label)
        ax.fill_between(np.arange(1, n + 1), pop.min(axis=0), pop.max(axis=0), color=color,
                        alpha=0.15, lw=0)
        peaks = [r.targets["peak_n"] for r in runs]
        print(f"{label}: peak median {np.median(peaks):.0f}, the arc in "
              f"{sum(r.arc for r in runs)} of {len(runs)}")
    d, c = zip(*u25.CENSUS)
    ax.scatter(d, c, color="#8B1E1E", zorder=3, s=28, label="Calhoun's census")
    ax.set_xlabel("day")
    ax.set_ylabel("mice (median; band: min-max over seeds)")
    ax.legend(frameon=False)
    out = Path("examples_out")
    out.mkdir(exist_ok=True)
    fig.savefig(out / "experiment.png", dpi=150, bbox_inches="tight")
    print(f"plot: {out / 'experiment.png'}")
