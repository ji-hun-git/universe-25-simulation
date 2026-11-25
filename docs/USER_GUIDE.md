# Universe 25 simulation — user guide

An agent-based simulation of John B. Calhoun's Universe 25 (1968–1973): a mouse colony with
unlimited food and water in a 101 × 101 in pen with 256 nest boxes. It grew from 8 mice to a
peak of 2,200, stopped breeding and died out. Each simulated mouse has needs (hunger, thirst,
fatigue, stress, social drive, aggression, maternal investment) and acts on them every few
hours of simulated time (every four hours). Nothing in the model schedules the collapse. It comes from crowding,
stress, failed maternal care and young who never develop adult social behaviour.

Use it to watch the colony, to run it under changed conditions, or as a substrate for your own
models. Please read "What it is not" before you draw conclusions from it.

## Install

Python 3.11 or newer.

```bash
git clone https://github.com/ji-hun-git/universe25-play
cd universe25-play
python -m venv .venv
.venv\Scripts\activate          # Windows; on macOS / Linux: source .venv/bin/activate
pip install -e .
```

The package runs from the clone. It reads its colonies from `configs/` and its measurements
from `scripts/`. NumPy 2 is required, and runs are the same only within one NumPy major version.

## Your first run

```bash
universe25 colonies                              # the colonies, and how close each comes
universe25 run --seed 7001 --out runs/first --plot
```

The second command runs Universe 25 in Calhoun's pen for 1,600 days, about a minute on one CPU
core. It prints the run beside Calhoun's record and writes these files to `runs/first/`:
- `run.json`: the numbers and the daily population;
- `population.csv`: one row per day;
- `population.png`: the population against Calhoun's censuses.

From Python:

```python
import universe25 as u25

r = u25.run("universe25", seed=7001)
print(r.table())             # the record's 14 numbers and 6 behavioural ones, beside this run
r.population                 # mice alive at the end of each day (index 0 is day 1)
r.targets["peak_n"], r.arc   # one number; whether the run shows Calhoun's arc
r.plot("population.png")
```

**Seeds** run from 7000 to 9999; the repo keeps a seed ledger (`docs/SEEDS.md`). The same
colony, seed, days and overrides always give the same run. Seeds 9160–9199 and 9464–9471 are
held back for the repo's own future validations, so please use others.

## The colonies

| name | what it is | use it for |
|---|---|---|
| `universe25` (default) | Calhoun's own pen layout: triangular cells, four box levels, food hoppers and water platforms with their capacities, no playground. Fitted to the record. | anything about Universe 25 itself |
| `reference` | Calhoun's sizes in a simplified pen: a 4 × 4 grid, nest boxes as points, unlimited food and water points, and a playground of balls, tunnels and ramps that Calhoun never had. Fitted to the record's population curve. | the repo's play research; comparisons with its published results |
| `replica` | Calhoun's pen with the settings before any fit. | seeing what the fit changed |
| `scarce` | `reference` with food for 1,000 a day. | scarcity experiments |

`universe25 colonies` prints how close each comes to the record.

## How close it comes

This is `universe25` on 48 seeds that were never used to fit it (9112–9159). "Inside" means
Calhoun's number falls within the 5–95 % range of the 48 runs. Reproduce it with
`universe25 check --seeds 9112-9159`, about 10 minutes on 8 cores.

| measure | Calhoun | model, median [5–95 %] | inside |
|---|---:|---:|:---:|
| first litters (day) | 50–104 | 50 [50, 50] | yes |
| population, day 315 | 620 | 699 [439, 941] | yes |
| adults, day 315 (131 days or older) | 150 | 112 [69, 174] | yes |
| **peak population** | 2,200 | 2,490 [2,355, 2,607] | **no** |
| plateau onset (day) | 560 | 510 [475, 577] | yes |
| population, day 736 | 2,056 | 1,958 [1,879, 2,084] | yes |
| population, day 811 | 1,871 | 1,767 [1,676, 1,895] | yes |
| **population, day 960** | 1,650 | 1,320 [1,182, 1,489] | **no** |
| doubling time, phase B (days) | 55 | 51 [45, 57] | yes |
| doubling time, phase C (days) | 105–145 | 105 [89, 137] | yes |
| last surviving birth (day) | 600 | 698 [599, 907] | yes |
| **last conception (day)** | 920 | 1,096 [1,042, 1,200] | **no** |
| population, day 1,444 | 122 | 85 [56, 162] | yes |
| population, day 1,588 | 27 | 24 [11, 95] | yes |
| **the arc** (growth, a phase with no surviving young, collapse) | yes | 46 of 48 runs | |

**The population curve: 11 of 14 inside.** The colony peaks about 300 mice too high, thins too
fast after day 800 and stops conceiving about 170 days late.

**The behaviour is not Calhoun's:**

| measure | Calhoun | model, median |
|---|---:|---:|
| withdrawn share of the weaned, day 560 | 0.32 | 0.10 |
| never fought as adults or mated (aged 131–320 days), day 800 — his "beautiful ones" | 0.53 | 0.00 |
| male share, day 315 | 0.40 | 0.50 |
| male share, day 1,444 | 0.18 | 0.45 |
| brood groups by day 315 | 14 | 29 |
| empty nest boxes, day 560 | 0.25 | 0.29 |

So the model reproduces how many mice there were, not how they behaved. The repo tried to close
this gap several times: three record fits (`docs/RECORD_FIT*.md`) and a model of the "deprived
generation" in five revisions (`docs/DEPRIVED_GENERATION.md`, off by default). None passed its
preregistered test. The record of all of it is in `NOTES.md`.

**With fewer seeds, fewer numbers fall inside**, because the ranges are narrower. Use 48 seeds
for a check you want to compare with these.

## Changing the model

Any config value can be changed on top of a colony.

```bash
universe25 run --set biology.litter_mean=4 --set initial_pairs=8 --out runs/small_litters
```

```python
r = u25.run("universe25", seed=7001, overrides={"biology": {"litter_mean": 4.0}})
```

Every field, with its meaning, is in `src/universe25/config.py`. A few to start with:

| key | the colony's value | what it is |
|---|---|---|
| `initial_pairs` | 4 | founding pairs |
| `biology.litter_mean` | 4.9 (fitted) | mean litter size |
| `biology.gestation_days` | 19.5 | gestation (days) |
| `biology.weaning_days` | 21 | weaning age (days) |
| `biology.maturity_days` | 64.5 (fitted) | age of sexual maturity (days) |
| `drives.stress_density_gain` | 0.46 (fitted) | how strongly crowding raises stress |
| `playground.enabled` | off (on in `reference`) | the playground of balls, tunnels and ramps |

The run's length is an argument (`--days`, `days=`), not an override.
`u25.colony_config(name).biology` shows every value a colony uses.

For a comparison, run both arms on the same seeds and compare their distributions
(`examples/03_experiment.py`). One seed is one stochastic history, not a result.

## Many seeds

```python
if __name__ == "__main__":        # needed on Windows: run_many starts worker processes
    runs = u25.run_many("universe25", seeds=range(7000, 7048), workers=8)
    check = u25.record_check(runs)
    print(check.table())          # the record against the runs' 5-95 % ranges
```

Each 1,600-day run takes about a minute on one core. `universe25 check --seeds 7000-7047
--out runs/check` does the same from the command line and writes `check.json`, with every run.

## Going deeper

- **Every mouse.** Step the engine yourself and read the arrays: `alive`, `sex`, `age_days`, `x`,
  `y`, `stress`, `hunger`, `role`, `nest_id`, `competence`, `maternal` and more
  (`src/universe25/agents/state.py`; `examples/04_inside_the_colony.py`).
- **Full logs.** The research engine writes per-window metrics (Parquet) and snapshots:
  `universe25 --seed 7001 --out runs/full --config configs/default.yaml` (README, "Quick start").
- **Watch it.** `universe25-app` opens the viewer: the pen from above and in 3D, recordings, live
  runs and a dashboard (README, "Viewer" and "App"). It needs an internet connection for two
  JavaScript libraries.
- **On a GPU.** A Warp path exists for NVIDIA GPUs (`pip install -e .[gpu]`). It is fast, but it
  is not the fitted colony, and several model options are NumPy-only.

## What it is not

- **Fitted, not predicted.** Its parameters were tuned to the record. That the fit holds on
  unseen seeds shows it is robust to chance, not that the model explains Universe 25. Many
  settings fit about as well.
- **One colony, one account.** The record is one colony, described mostly by Calhoun himself. The
  model follows his reading.
- **The collapse is built in.** In the model, young raised in a broken colony never recover, as
  Calhoun reported. Other rodent colonies recovered when thinned or moved (`docs/PRIOR_WORK.md`).
- **The behaviour does not match** (above). Claims about the beautiful ones or withdrawal need
  more than this model.
- **Simplified space.** The pen is a plane. Mice do not climb, and the four box levels are
  labels.
- **Not a model of people.** Universe 25 is often quoted about human societies. Nothing here
  supports that.

## Citing

Please cite Calhoun's paper for the colony and this repository for the simulation:
- Calhoun, J. B. (1973). Death squared: the explosive growth and demise of a mouse population.
  *Proceedings of the Royal Society of Medicine*, 66(1 Pt 2), 80–88.
- universe25-play, https://github.com/ji-hun-git/universe25-play (give the commit you used).

## License

MIT (`LICENSE`). Not affiliated with Calhoun's estate or the NIMH.
