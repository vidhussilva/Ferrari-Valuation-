"""Reconcile the Python engine against the Excel workbook's calculated outputs."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import engine
from .excel_io import SERIES_OUTPUTS, VALUE_OUTPUTS, ModelInputs, load_inputs, read_outputs
from .layout import FCST_YEARS, SCENARIOS
from .libreoffice import recalculate
from .sensitivity import GRID_STEPS

REL_TOL = 1e-6  # |excel - python| <= REL_TOL * max(1, |excel|)


def _python_series(v: engine.Valuation) -> dict:
    p = v.projection
    out = {key: p.loc[key].to_numpy(dtype=float) for _, _, _, key in SERIES_OUTPUTS if key in p.index}
    out["discount_factor"] = v.discount_factor
    out["pv_ufcf"] = v.pv_ufcf
    return out


def compare(inp: ModelInputs, excel: dict) -> pd.DataFrame:
    """Line-by-line comparison for the scenario the workbook was calculated under."""
    scenario = SCENARIOS[int(excel["scenario"]) - 1]
    v = engine.value(inp, scenario)
    py_series = _python_series(v)
    py_values = v.summary()
    rows = []

    def add(area, item, period, x, p):
        rows.append((scenario, area, item, period, float(x), float(p)))

    for area, _, _, key in SERIES_OUTPUTS:
        for y, x, p in zip(FCST_YEARS, excel["series"][key], py_series[key]):
            add(area, key, str(y), x, p)
    for area, _, _, key in VALUE_OUTPUTS:
        add(area, key, "", excel["values"][key], py_values[key])

    ufcf = v.projection.loc["ufcf"].to_numpy(dtype=float)
    waccs = v.wacc["wacc"] + GRID_STEPS * inp.sens_steps[0]
    tgrs = v.tgr + GRID_STEPS * inp.sens_steps[1]
    per_share, ev = engine.dcf_grid(ufcf, engine.discount_periods(inp), waccs, tgrs, inp.nid, inp.shares)
    for key, grid in (("value_per_share", per_share), ("enterprise_value", ev)):
        xl = excel["grids"][key]
        for i, w in enumerate(waccs):
            add("Sensitivity grid", f"{key} | WACC", f"row {i + 1}", xl["wacc"][i], w)
            for j, g in enumerate(tgrs):
                add("Sensitivity grid", key, f"WACC {w:.2%} / g {g:.2%}", xl["grid"][i, j], grid[i, j])
        for j, g in enumerate(tgrs):
            add("Sensitivity grid", f"{key} | g", f"col {j + 1}", xl["tgr"][j], g)

    df = pd.DataFrame(rows, columns=["scenario", "area", "item", "period", "excel", "python"])
    df["abs_diff"] = (df["excel"] - df["python"]).abs()
    df["passed"] = df["abs_diff"] <= REL_TOL * np.maximum(1.0, df["excel"].abs())
    return df


def reconcile_workbook(model: str | Path, all_scenarios: bool = False, recalc: bool = False,
                       workdir: str | Path = "outputs/recalculated") -> pd.DataFrame:
    """Reconcile the saved workbook, or recalculate it under each scenario with LibreOffice first."""
    model = Path(model)
    inp = load_inputs(model)
    if all_scenarios:
        paths = [recalculate(model, workdir, scenario=s) for s in (1, 2, 3)]
    elif recalc:
        paths = [recalculate(model, workdir)]
    else:
        paths = [model]
    return pd.concat([compare(inp, read_outputs(p)) for p in paths], ignore_index=True)


def write_report(df: pd.DataFrame, out_dir: str | Path, model: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "reconciliation_detail.csv", index=False)
    lines = [
        "# Excel vs Python reconciliation",
        "",
        f"Workbook: `{Path(model).as_posix()}`  ",
        f"Tolerance: |Excel - Python| <= {REL_TOL:g} x max(1, |Excel|)",
        "",
        "| Scenario | Area | Items compared | Max abs. difference | Result |",
        "|---|---|---:|---:|---|",
    ]
    for (sc, area), g in df.groupby(["scenario", "area"], sort=False):
        lines.append(f"| {sc} | {area} | {len(g)} | {g.abs_diff.max():.2e} | {'PASS' if g.passed.all() else 'FAIL'} |")
    key_items = ["wacc", "enterprise_value", "equity_value", "value_per_share", "upside"]
    lines += ["", "## Key valuation outputs", "", "| Scenario | Output | Excel | Python | Difference |", "|---|---|---:|---:|---:|"]
    for _, r in df[(df.area.isin(["WACC", "Valuation"])) & (df["item"].isin(key_items))].iterrows():
        fmt = "{:.4%}" if r["item"] in ("wacc", "upside") else "{:,.4f}"
        lines.append(f"| {r.scenario} | {r['item']} | {fmt.format(r.excel)} | {fmt.format(r.python)} | {r.abs_diff:.2e} |")
    status = "ALL ITEMS RECONCILE" if df.passed.all() else f"{(~df.passed).sum()} ITEM(S) OUTSIDE TOLERANCE"
    lines += ["", f"**{status}** ({len(df):,} comparisons). Full detail: `reconciliation_detail.csv`.", ""]
    path = out_dir / "reconciliation_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
