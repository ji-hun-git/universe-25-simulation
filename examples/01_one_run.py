"""One run of Universe 25 in Calhoun's pen, beside his record, with a plot.

    python examples/01_one_run.py

About a minute on one CPU core. Writes examples_out/one_run.png.
"""
from pathlib import Path

import universe25 as u25

out = Path("examples_out")
out.mkdir(exist_ok=True)
r = u25.run("universe25", seed=7001)  # 1,600 days, as Calhoun's colony ran
print(r.table())
print(f"\npeak {r.targets['peak_n']:.0f} mice; the arc (growth, no surviving young, collapse): "
      f"{'yes' if r.arc else 'no'}")
r.plot(out / "one_run.png")
print(f"plot: {out / 'one_run.png'}")
