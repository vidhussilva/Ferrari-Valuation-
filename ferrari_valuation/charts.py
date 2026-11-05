"""Static PNG charts for the sensitivity outputs (matplotlib)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
SERIES = {"Bear": "#eb6834", "Base": "#2a78d6", "Bull": "#1baf7a"}  # validated categorical slots
UP, DOWN = "#2a78d6", "#eb6834"
DIVERGING = LinearSegmentedColormap.from_list(
    "red_grey_blue", ["#b8302f", "#e34948", "#f3b2b1", "#f0efec", "#9ec5f4", "#3987e5", "#1c5cab"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT_2, "xtick.color": TEXT_2, "ytick.color": TEXT_2,
    "text.color": TEXT, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
})


def _save(fig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def wacc_tgr_heatmap(table, share_price, path, title="Implied value per share (EUR) - Base case"):
    values = table.to_numpy()
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    span = max(values.max() - share_price, share_price - values.min())
    norm = TwoSlopeNorm(vcenter=share_price, vmin=share_price - span, vmax=share_price + span)
    ax.imshow(values, cmap=DIVERGING, norm=norm, aspect="auto")
    ax.set_xticks(range(values.shape[1]), [f"{g:.2%}" for g in table.columns])
    ax.set_yticks(range(values.shape[0]), [f"{w:.2%}" for w in table.index])
    ax.set_xlabel("Terminal growth rate")
    ax.set_ylabel("WACC")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            v = values[i, j]
            dark = abs(norm(v) - 0.5) > 0.32
            ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=9,
                    color="white" if dark else TEXT, fontweight="bold" if (i, j) == (3, 3) else "normal")
    ax.add_patch(plt.Rectangle((2.5, 2.5), 1, 1, fill=False, edgecolor=TEXT, linewidth=1.6))
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(title, pad=24)
    ax.text(0, 1.015, f"Blue = above, red = below the EUR {share_price:,.1f} share price (31-Dec-2025); boxed cell = base case",
            transform=ax.transAxes, fontsize=9, color=TEXT_2)
    return _save(fig, path)


def tornado_chart(df, path, title="What moves the value? One-at-a-time sensitivities (Base case)"):
    df = df.iloc[::-1].reset_index(drop=True)
    base = float(df["base_value"].iloc[0])
    fig, ax = plt.subplots(figsize=(9, 5.6))
    y = np.arange(len(df))
    h = 0.62
    for label, col, color in [("Input lowered", "value_at_low_input", DOWN), ("Input raised", "value_at_high_input", UP)]:
        delta = df[col] - base
        ax.barh(y, delta, left=base, height=h, color=color, label=label, edgecolor=SURFACE, linewidth=1)
    for i, row in df.iterrows():
        lo, hi = sorted([row.value_at_low_input, row.value_at_high_input])
        ax.text(lo - 1.5, i, f"{lo:,.0f}", va="center", ha="right", fontsize=8.5, color=TEXT_2)
        ax.text(hi + 1.5, i, f"{hi:,.0f}", va="center", ha="left", fontsize=8.5, color=TEXT_2)
    ax.axvline(base, color=TEXT, linewidth=1)
    ax.set_yticks(y, df["driver"])
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Implied value per share (EUR)")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    lo_all = min(df.value_at_low_input.min(), df.value_at_high_input.min())
    hi_all = max(df.value_at_low_input.max(), df.value_at_high_input.max())
    pad = (hi_all - lo_all) * 0.12
    ax.set_xlim(lo_all - pad, hi_all + pad)
    ax.set_title(title, pad=16)
    ax.text(base, len(df) - 0.35, f" Base EUR {base:,.1f}", fontsize=9, color=TEXT, va="bottom")
    ax.legend(loc="lower right", frameon=False)
    return _save(fig, path)


def scenario_bars(summary, share_price, path, title="DCF value per share by scenario vs share price"):
    labels = ["Bear", "Base", "Bull", "Probability-weighted"]
    values = [summary.loc["value_per_share", k] for k in labels]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    x = np.arange(len(labels))
    ax.bar(x, values, width=0.55, color=SERIES["Base"], edgecolor=SURFACE, linewidth=2)
    for xi, v in zip(x, values):
        ax.text(xi, v / 2, f"EUR {v:,.0f}\n({v / share_price - 1:+.0%})", ha="center", va="center", fontsize=9.5,
                color="white", fontweight="bold")
    ax.axhline(share_price, color=TEXT, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(-0.45, share_price + 4, f"Share price EUR {share_price:,.1f} (31-Dec-2025)", ha="left", va="bottom",
            fontsize=9, color=TEXT)
    ax.set_xticks(x, ["Bear", "Base", "Bull", "Prob.-weighted\n(25/50/25)"])
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("EUR per share")
    ax.set_ylim(0, max(values + [share_price]) * 1.22)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title)
    return _save(fig, path)


def projection_panels(proj, path, title="Scenario projections, 2026E-2035E"):
    panels = [("revenue", "Net revenues (EUR bn)", 1e-3, "{:.1f}"),
              ("ebitda_margin", "EBITDA margin", 100, "{:.1f}%"),
              ("ufcf", "Unlevered free cash flow (EUR bn)", 1e-3, "{:.2f}")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for ax, (col, label, scale, fmt) in zip(axes, panels):
        for sc, color in SERIES.items():
            d = proj[proj.scenario == sc]
            yv = d[col].to_numpy() * scale
            ax.plot(d.year, yv, color=color, linewidth=2, label=sc)
            ax.text(d.year.iloc[-1] + 0.25, yv[-1], f"{sc} {fmt.format(yv[-1])}", color=TEXT, fontsize=8.5, va="center")
        ax.set_title(label, fontsize=11)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlim(2025.6, 2037.6)
        ax.set_xticks([2026, 2028, 2030, 2032, 2034])
        if col == "ebitda_margin":
            ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    axes[0].legend(loc="upper left", frameon=False)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    return _save(fig, path)


def monte_carlo_histogram(draws, summary, path, title="Monte Carlo: value per share, Base case"):
    values = draws["value_per_share"].to_numpy()
    cap = np.percentile(values, 99.5)  # long right tail from low WACC - g spreads; cut for readability
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    counts, _, _ = ax.hist(values[values <= cap], bins=60, color=SERIES["Base"], edgecolor=SURFACE, linewidth=0.6)
    top = counts.max() * 1.32  # headroom so the labels sit above the bars
    price, p10, p50, p90 = summary["share_price"], summary["p10"], summary["p50"], summary["p90"]
    ax.axvspan(p10, p90, color=GRID, alpha=0.45, zorder=0, linewidth=0)
    ax.axvline(price, color=TEXT, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(price + 4, top * 0.97, f"Share price EUR {price:,.1f}\n{summary['prob_above_share_price']:.0%} of draws above",
            ha="left", va="top", fontsize=9, color=TEXT)
    ax.axvline(p50, color=TEXT_2, linewidth=1)
    ax.text(p50 - 4, top * 0.97, f"Median EUR {p50:,.0f}", ha="right", va="top", fontsize=9, color=TEXT_2)
    ax.text(p90 + 4, top * 0.62, f"Shaded: P10-P90\nEUR {p10:,.0f} - {p90:,.0f}", ha="left", va="top", fontsize=9,
            color=TEXT_2)
    ax.set_ylim(0, top)
    ax.set_xlabel("Implied value per share (EUR)")
    ax.set_ylabel("Draws")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, pad=22)
    ax.text(0, 1.015, f"{int(summary['draws']):,} draws: WACC, terminal growth, price/mix growth, gross margin and capex "
            f"intensity; x-axis cut at the 99.5th percentile", transform=ax.transAxes, fontsize=9, color=TEXT_2)
    return _save(fig, path)
