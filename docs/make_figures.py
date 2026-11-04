"""Draw docs/pipeline_outputs.png from the CSV extracts in tableau/ (run the pipeline first).

    python docs/make_figures.py        # needs matplotlib
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "tableau"

weekly = pd.read_csv(T / "weekly_total.csv", parse_dates=["week"])
abc = pd.read_csv(T / "abc_products.csv")
bt = pd.read_csv(T / "backtest_summary.csv")

fig, axes = plt.subplots(1, 3, figsize=(14, 3.9), dpi=150, gridspec_kw={"width_ratios": [1.5, 1, 1.2]})
ax = axes[0]
ax.plot(weekly["week"], weekly["revenue"] / 1000, color="#1c7ed6", lw=1.6)
ax.set_title("Weekly revenue (complete weeks)", loc="left", fontsize=11)
ax.set_ylabel("revenue, thousand £", fontsize=9)
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

ax = axes[1]
share_products = abc["rank"] / len(abc)
ax.plot(share_products * 100, abc["cum_share"] * 100, color="#e8590c", lw=1.8)
n_a = int((abc["abc_class"] == "A").sum())
ax.axhline(80, color="#868e96", ls="--", lw=1)
ax.axvline(100 * n_a / len(abc), color="#868e96", ls="--", lw=1)
ax.text(100 * n_a / len(abc) + 2, 40, f"A class: {n_a:,} of {len(abc):,}\nproducts ({100 * n_a / len(abc):.0f}%)\n= 80% of revenue",
        fontsize=8.5, color="#495057")
ax.set_title("ABC classes (Pareto curve)", loc="left", fontsize=11)
ax.set_xlabel("% of products, by revenue", fontsize=9)
ax.set_ylabel("% of revenue", fontsize=9)

ax = axes[2]
bt = bt.sort_values("wape", ascending=False)
colors = ["#adb5bd"] * (len(bt) - 1) + ["#2f9e44"]
ax.barh(bt["method"], bt["wape"], color=colors)
for y, v in enumerate(bt["wape"]):
    ax.text(v + 0.01, y, f"{v:.3f}", va="center", fontsize=9)
ax.set_xlim(0, bt["wape"].max() * 1.2)
ax.set_title("Forecast backtest, top 50 A products", loc="left", fontsize=11)
ax.set_xlabel("WAPE, one week ahead (lower is better)", fontsize=9)
ax.tick_params(axis="y", labelsize=8.5)

for a in axes:
    a.spines[["top", "right"]].set_visible(False)
    a.tick_params(labelsize=8.5)
fig.tight_layout()
fig.savefig(ROOT / "docs" / "pipeline_outputs.png", facecolor="white")
print("docs/pipeline_outputs.png")
