"""Read the model's hard-coded inputs and its computed outputs from the Excel workbook.

Inputs are located by row label (see layout.py), so the Python engine never depends on
hard-coded cell addresses. Only literal input cells are read as inputs; anything the
workbook derives with a formula is recomputed independently in engine.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

from .layout import (
    AL, BSL, CFL, COMMON_DRIVERS, DL, FCST_YEARS, HIST_YEARS, HL, ISL, S, SCENARIO_DRIVERS,
    SCENARIO_ROW_LABELS, SCENARIOS, VALUE_COL, WL, YEAR_COL,
)

FCST_COLS = [YEAR_COL[y] for y in FCST_YEARS]


def label_index(ws, col=1):
    """Map each non-empty label in `col` to the list of rows it appears on."""
    index: dict[str, list[int]] = {}
    for row in ws.iter_rows(min_col=col, max_col=col):
        cell = row[0]
        if isinstance(cell.value, str):
            index.setdefault(cell.value.strip(), []).append(cell.row)
    return index


def find_row(ws, label, index=None):
    rows = (index or label_index(ws)).get(label, [])
    if len(rows) != 1:
        raise KeyError(f"{ws.title}: expected exactly one row labelled {label!r}, found {len(rows)}")
    return rows[0]


def _number(ws, addr):
    v = ws[addr].value
    if isinstance(v, str) and v.startswith("="):
        raise ValueError(f"{ws.title}!{addr} is a formula; expected a hard-coded input")
    if v is None:
        raise ValueError(f"{ws.title}!{addr} is empty")
    return float(v)


@dataclass(frozen=True)
class ModelInputs:
    """Everything the engine needs, exactly as typed into the workbook."""

    scenario: int
    share_price_usd: float
    eurusd: float
    shares: float
    tgr: float
    mid_year: float
    nid: float
    scenario_drivers: dict  # key -> {"Bear": array, "Base": array, "Bull": array}
    common: dict  # key -> array over FCST_YEARS
    wacc: dict  # rf, raw_beta, blume_weight, erp, kd, tax
    hist: dict  # HL attribute -> {year: value} (literal inputs only)
    sens_steps: tuple  # (WACC step, terminal-growth step)

    @property
    def share_price(self) -> float:
        return self.share_price_usd / self.eurusd


def load_inputs(path: str | Path) -> ModelInputs:
    wb = load_workbook(path, data_only=False)

    a = wb[S.ASSUMP]
    ai = label_index(a)

    def single(label):
        return _number(a, f"{VALUE_COL}{find_row(a, label, ai)}")

    def row_values(ws, r):
        return np.array([_number(ws, f"{c}{r}") for c in FCST_COLS])

    scenario_drivers = {}
    for key, label, _ in SCENARIO_DRIVERS:
        live = find_row(a, label, ai)
        block = {}
        for offset, (sc, sc_label) in enumerate(zip(SCENARIOS, SCENARIO_ROW_LABELS), start=1):
            if a.cell(live + offset, 1).value != sc_label:
                raise KeyError(f"Assumptions: expected {sc_label!r} {offset} row(s) below {label!r}")
            block[sc] = row_values(a, live + offset)
        scenario_drivers[key] = block
    common = {key: row_values(a, find_row(a, label, ai)) for key, label, _ in COMMON_DRIVERS}

    w = wb[S.WACC]
    wi = label_index(w)
    wacc = {k: _number(w, f"{VALUE_COL}{find_row(w, lbl, wi)}") for k, lbl in [
        ("rf", WL.rf), ("raw_beta", WL.raw_beta), ("blume_weight", WL.blume_weight),
        ("erp", WL.erp), ("kd", WL.kd), ("tax", WL.tax)]}

    h = wb[S.HIST]
    hi = label_index(h)
    hist = {}
    for attr, label in vars(HL).items():
        if attr.startswith("_"):
            continue
        r = find_row(h, label, hi)
        vals = {}
        for y in HIST_YEARS:
            v = h[f"{YEAR_COL[y]}{r}"].value
            if isinstance(v, (int, float)):
                vals[y] = float(v)
        hist[attr] = vals

    sens = wb[S.SENS]
    si = label_index(sens)
    steps = (_number(sens, f"C{find_row(sens, 'WACC step', si)}"),
             _number(sens, f"C{find_row(sens, 'Terminal growth step', si)}"))

    return ModelInputs(
        scenario=int(single(AL.scenario)), share_price_usd=single(AL.share_price_usd), eurusd=single(AL.eurusd),
        shares=single(AL.shares), tgr=single(AL.tgr), mid_year=single(AL.mid_year), nid=single(AL.nid),
        scenario_drivers=scenario_drivers, common=common, wacc=wacc, hist=hist, sens_steps=steps,
    )


# ----------------------------------------------------------------------------- outputs
# (area, sheet, label, output key) for the forecast line items that are reconciled.
SERIES_OUTPUTS = [
    ("Revenue build", S.REV, "Shipments", "shipments"),
    ("Income statement", S.IS, ISL.revenue, "revenue"),
    ("Income statement", S.IS, ISL.gross_profit, "gross_profit"),
    ("Income statement", S.IS, ISL.ebitda, "ebitda"),
    ("Income statement", S.IS, ISL.ebit, "ebit"),
    ("Income statement", S.IS, ISL.net_fin, "net_fin"),
    ("Income statement", S.IS, ISL.net_profit, "net_profit"),
    ("Income statement", S.IS, ISL.eps, "eps"),
    ("Balance sheet", S.BS, BSL.cash, "cash"),
    ("Balance sheet", S.BS, BSL.total_assets, "total_assets"),
    ("Balance sheet", S.BS, BSL.debt, "debt"),
    ("Balance sheet", S.BS, BSL.equity, "equity"),
    ("Balance sheet", S.BS, BSL.nwc, "nwc"),
    ("Balance sheet", S.BS, BSL.check, "bs_check"),
    ("Balance sheet", S.BS, BSL.shares, "shares"),
    ("Cash flow", S.CF, CFL.cfo, "cfo"),
    ("Cash flow", S.CF, CFL.capex, "capex"),
    ("Cash flow", S.CF, CFL.dividends, "dividends"),
    ("Cash flow", S.CF, CFL.buybacks, "buybacks"),
    ("Cash flow", S.CF, CFL.cash_end, "cash_end"),
    ("DCF", S.DCF, DL.ufcf, "ufcf"),
    ("DCF", S.DCF, DL.df, "discount_factor"),
    ("DCF", S.DCF, DL.pv, "pv_ufcf"),
]

VALUE_OUTPUTS = [
    ("WACC", S.WACC, WL.beta, "beta"),
    ("WACC", S.WACC, WL.ke, "ke"),
    ("WACC", S.WACC, WL.kd_at, "kd_after_tax"),
    ("WACC", S.WACC, WL.wacc, "wacc"),
    ("Valuation", S.DCF, DL.sum_pv, "sum_pv"),
    ("Valuation", S.DCF, DL.tv, "terminal_value"),
    ("Valuation", S.DCF, DL.pv_tv, "pv_terminal_value"),
    ("Valuation", S.DCF, DL.ev, "enterprise_value"),
    ("Valuation", S.DCF, DL.tv_pct, "tv_pct_of_ev"),
    ("Valuation", S.DCF, DL.equity, "equity_value"),
    ("Valuation", S.DCF, DL.value_ps, "value_per_share"),
    ("Valuation", S.DCF, DL.upside, "upside"),
]

SENS_TABLES = {"value_per_share": "Implied value per share (€)", "enterprise_value": "Enterprise value (€m)"}


def read_outputs(path: str | Path) -> dict:
    """Cached (calculated) values of the reconciled outputs.

    The workbook must have been calculated and saved by Excel or LibreOffice; a file
    written by openpyxl alone has no cached values (see libreoffice.recalculate)."""
    wb = load_workbook(path, data_only=True)
    out = {"scenario": None, "series": {}, "values": {}, "grids": {}}
    a = wb[S.ASSUMP]
    out["scenario"] = a[f"{VALUE_COL}{find_row(a, AL.scenario)}"].value
    indexes = {}

    def idx(sheet):
        if sheet not in indexes:
            indexes[sheet] = label_index(wb[sheet])
        return indexes[sheet]

    for _, sheet, label, key in SERIES_OUTPUTS:
        ws = wb[sheet]
        r = find_row(ws, label, idx(sheet))
        out["series"][key] = np.array([ws[f"{c}{r}"].value for c in FCST_COLS], dtype=float)
    for _, sheet, label, key in VALUE_OUTPUTS:
        ws = wb[sheet]
        out["values"][key] = ws[f"{VALUE_COL}{find_row(ws, label, idx(sheet))}"].value
    sens = wb[S.SENS]
    for key, title in SENS_TABLES.items():
        top = find_row(sens, title, idx(S.SENS))
        hdr = top + 1
        g = np.array([sens.cell(hdr, c).value for c in range(3, 10)], dtype=float)
        w = np.array([sens.cell(hdr + 1 + i, 2).value for i in range(7)], dtype=float)
        grid = np.array([[sens.cell(hdr + 1 + i, c).value for c in range(3, 10)] for i in range(7)], dtype=float)
        out["grids"][key] = {"wacc": w, "tgr": g, "grid": grid}
    if any(v is None for v in out["values"].values()):
        raise ValueError(f"{path} has no cached values - recalculate it in Excel/LibreOffice first "
                         "(python scripts/reconcile_with_excel.py --recalc)")
    return out
