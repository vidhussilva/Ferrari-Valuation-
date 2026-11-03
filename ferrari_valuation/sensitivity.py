"""Automated sensitivity analysis on top of the Python engine.

- scenario_summary:   Bear / Base / Bull outputs plus a probability-weighted value
- wacc_tgr_table:     WACC x terminal-growth grid (same steps as the Excel Sensitivity sheet)
- tornado:            one-at-a-time flex of each key driver around the base case
- growth_margin_grid: revenue growth (price/mix) x gross-margin shifts
- reverse_dcf:        lever values, one at a time, at which the DCF equals the share price
- exit_multiple_table: WACC x exit EV/EBITDA grid, cross-checking the Gordon-growth terminal value
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import engine
from .excel_io import ModelInputs
from .layout import FCST_YEARS, SCENARIOS

SCENARIO_WEIGHTS = {"Bear": 0.25, "Base": 0.50, "Bull": 0.25}
GRID_STEPS = np.arange(-3, 4)
EXIT_MULTIPLES = np.arange(12.0, 22.1, 2.0)  # EV / 2035E EBITDA

# (label, kind, target, low, high); kind is "shock" (driver row), "wacc", "tgr" or "capm" (WACC-sheet input)
TORNADO_SPECS = [
    ("WACC +/-0.5pt", "wacc", None, -0.005, 0.005),
    ("Terminal growth +/-0.5pt", "tgr", None, -0.005, 0.005),
    ("Gross margin +/-1.0pt", "shock", "gross_margin", -0.01, 0.01),
    ("Price / mix growth +/-1.0pt p.a.", "shock", "price_mix_growth", -0.01, 0.01),
    ("Shipments growth +/-1.0pt p.a.", "shock", "shipments_growth", -0.01, 0.01),
    ("Sponsorship & brand growth +/-2.0pt p.a.", "shock", "sponsorship_growth", -0.02, 0.02),
    ("Capex intensity +/-1.0pt of revenue", "shock", "capex_pct", -0.01, 0.01),
    ("R&D intensity +/-0.5pt of revenue", "shock", "rnd_pct", -0.005, 0.005),
    ("Effective tax rate +/-2.0pt", "shock", "tax_rate", -0.02, 0.02),
    ("Customer advances +/-2.0pt of revenue", "shock", "ol_pct", -0.02, 0.02),
    ("Equity risk premium +/-0.5pt", "capm", "erp", -0.005, 0.005),
    ("Raw beta +/-0.10", "capm", "raw_beta", -0.10, 0.10),
]

# (label, kind, target, search bracket around the base level); kind as in TORNADO_SPECS
REVERSE_DCF_LEVERS = [
    ("Price / mix growth (avg. p.a.)", "shock", "price_mix_growth", (-0.05, 0.05)),
    ("Gross margin (avg.)", "shock", "gross_margin", (-0.10, 0.10)),
    ("WACC", "wacc", None, (-0.03, 0.03)),
    ("Terminal growth", "tgr", None, (-0.02, 0.02)),
]


def scenario_summary(inp: ModelInputs, weights: dict = SCENARIO_WEIGHTS) -> pd.DataFrame:
    cols = {sc: engine.value(inp, sc).summary() for sc in SCENARIOS}
    df = pd.DataFrame(cols)
    df.loc["weight"] = [weights[sc] for sc in SCENARIOS]
    weighted = sum(weights[sc] * df.loc["value_per_share", sc] for sc in SCENARIOS)
    df["Probability-weighted"] = np.nan
    df.loc["value_per_share", "Probability-weighted"] = weighted
    df.loc["upside", "Probability-weighted"] = weighted / inp.share_price - 1
    df.loc["weight", "Probability-weighted"] = sum(weights.values())
    return df


def wacc_tgr_table(inp: ModelInputs, scenario=None, steps: tuple | None = None, metric: str = "value_per_share"):
    """Grid centred on the model WACC / terminal growth, matching the Excel Sensitivity sheet."""
    base = engine.value(inp, scenario)
    w_step, g_step = steps or inp.sens_steps
    waccs = base.wacc["wacc"] + GRID_STEPS * w_step
    tgrs = base.tgr + GRID_STEPS * g_step
    ufcf = base.projection.loc["ufcf"].to_numpy(dtype=float)
    per_share, ev = engine.dcf_grid(ufcf, engine.discount_periods(inp), waccs, tgrs, inp.nid, inp.shares)
    grid = per_share if metric == "value_per_share" else ev
    return pd.DataFrame(grid, index=pd.Index(waccs, name="WACC"), columns=pd.Index(tgrs, name="Terminal growth"))


def tornado(inp: ModelInputs, scenario: str = "Base") -> pd.DataFrame:
    base = engine.value(inp, scenario)
    rows = []
    for label, kind, target, low, high in TORNADO_SPECS:
        values = []
        for delta in (low, high):
            if kind == "shock":
                v = engine.value(inp, scenario, shocks={target: delta})
            elif kind == "wacc":
                v = engine.value(inp, scenario, wacc=base.wacc["wacc"] + delta)
            elif kind == "tgr":
                v = engine.value(inp, scenario, tgr=base.tgr + delta)
            else:
                v = engine.value(inp, scenario, wacc_overrides={target: inp.wacc[target] + delta})
            values.append(v.value_per_share)
        rows.append({"driver": label, "value_at_low_input": values[0], "value_at_high_input": values[1],
                     "base_value": base.value_per_share, "swing": abs(values[1] - values[0])})
    return pd.DataFrame(rows).sort_values("swing", ascending=False).reset_index(drop=True)


def gordon_implied_multiple(v: engine.Valuation) -> float:
    """Terminal EV / EBITDA implied by the Gordon-growth terminal value."""
    return v.terminal_value / v.projection.loc["ebitda"].iloc[-1]


def exit_multiple_table(inp: ModelInputs, scenario=None, multiples=EXIT_MULTIPLES, wacc_step: float | None = None):
    """Value per share with an exit-multiple terminal value: WACC (rows) x EV / 2035E EBITDA (columns)."""
    base = engine.value(inp, scenario)
    waccs = base.wacc["wacc"] + GRID_STEPS * (inp.sens_steps[0] if wacc_step is None else wacc_step)
    p = base.projection
    per_share, _ = engine.exit_multiple_grid(p.loc["ufcf"].to_numpy(dtype=float), p.loc["ebitda"].iloc[-1],
                                             engine.discount_periods(inp), waccs, multiples, inp.nid, inp.shares)
    return pd.DataFrame(per_share, index=pd.Index(waccs, name="WACC"),
                        columns=pd.Index(np.asarray(multiples, dtype=float), name="Exit EV / 2035E EBITDA"))


def breakeven_exit_multiple(inp: ModelInputs, scenario=None, target_price: float | None = None) -> float:
    """Exit EV / 2035E EBITDA at which the DCF value per share equals the share price (at the model WACC)."""
    target = inp.share_price if target_price is None else target_price
    v = engine.value(inp, scenario)
    tv_needed = (target * inp.shares + inp.nid - v.sum_pv) * (1 + v.wacc["wacc"]) ** len(v.pv_ufcf)
    return tv_needed / v.projection.loc["ebitda"].iloc[-1]


def growth_margin_grid(inp: ModelInputs, scenario: str = "Base", growth_shifts=None, margin_shifts=None) -> pd.DataFrame:
    """Value per share when revenue-per-car growth (rows) and gross margin (columns) shift by the given points."""
    growth_shifts = np.arange(-0.02, 0.0201, 0.01) if growth_shifts is None else np.asarray(growth_shifts)
    margin_shifts = np.arange(-0.02, 0.0201, 0.01) if margin_shifts is None else np.asarray(margin_shifts)
    grid = [[engine.value(inp, scenario, shocks={"price_mix_growth": dg, "gross_margin": dm}).value_per_share
             for dm in margin_shifts] for dg in growth_shifts]
    return pd.DataFrame(grid, index=pd.Index(growth_shifts, name="Price/mix growth shift (pts p.a.)"),
                        columns=pd.Index(margin_shifts, name="Gross margin shift (pts)"))


def _bisect(f, lo, hi, tol=1e-6, max_iter=200):
    """Root of a monotonic f on [lo, hi]."""
    f_lo, f_hi = f(lo), f(hi)
    if np.sign(f_lo) == np.sign(f_hi):
        raise ValueError(f"no root between {lo:.4f} and {hi:.4f} (f = {f_lo:.2f}, {f_hi:.2f})")
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if abs(f_mid) < tol:
            break
        if np.sign(f_mid) == np.sign(f_lo):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return mid


def reverse_dcf(inp: ModelInputs, scenario: str = "Base", target_price: float | None = None) -> pd.DataFrame:
    """Back out, one lever at a time, the assumption at which the DCF value per share equals the share price.

    Driver levers are uniform shifts applied to every forecast year, reported as the average level over 2026E-2035E."""
    target = inp.share_price if target_price is None else target_price
    base = engine.value(inp, scenario)
    d = engine.drivers(inp, scenario)
    rows = []
    for label, kind, key, (lo, hi) in REVERSE_DCF_LEVERS:
        if kind == "shock":
            level = d[key].mean()
            value_at = lambda x, key=key: engine.value(inp, scenario, shocks={key: x}).value_per_share  # noqa: E731
        elif kind == "wacc":
            level = base.wacc["wacc"]
            value_at = lambda x, level=level: engine.value(inp, scenario, wacc=level + x).value_per_share  # noqa: E731
        else:
            level = base.tgr
            value_at = lambda x, level=level: engine.value(inp, scenario, tgr=level + x).value_per_share  # noqa: E731
        change = _bisect(lambda x: value_at(x) - target, lo, hi)
        rows.append({"lever": label, "base_level": level, "implied_level": level + change, "change": change,
                     "value_per_share": value_at(change), "share_price": target})
    return pd.DataFrame(rows)


def projections_by_scenario(inp: ModelInputs) -> pd.DataFrame:
    frames = []
    for sc in SCENARIOS:
        p = engine.project(inp, sc)
        frames.append(pd.DataFrame({
            "scenario": sc, "year": FCST_YEARS, "revenue": p.loc["revenue"].values,
            "ebitda_margin": (p.loc["ebitda"] / p.loc["revenue"]).values, "net_profit": p.loc["net_profit"].values,
            "ufcf": p.loc["ufcf"].values, "eps": p.loc["eps"].values,
        }))
    return pd.concat(frames, ignore_index=True)


def run_all(inp: ModelInputs) -> dict:
    return {
        "scenario_summary": scenario_summary(inp),
        "wacc_g_value_per_share": {sc: wacc_tgr_table(inp, sc) for sc in SCENARIOS},
        "wacc_g_enterprise_value": wacc_tgr_table(inp, "Base", metric="enterprise_value"),
        "tornado": tornado(inp, "Base"),
        "growth_margin": growth_margin_grid(inp, "Base"),
        "reverse_dcf": reverse_dcf(inp, "Base"),
        "exit_multiple": {sc: exit_multiple_table(inp, sc) for sc in SCENARIOS},
        "projections": projections_by_scenario(inp),
    }
