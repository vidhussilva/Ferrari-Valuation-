"""Model integrity tests: python -m pytest -q"""
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ferrari_valuation import engine, sensitivity  # noqa: E402
from ferrari_valuation.excel_io import find_row, load_inputs  # noqa: E402
from ferrari_valuation.layout import BSL, S, SCENARIOS, YEAR_COL  # noqa: E402
from ferrari_valuation.reconcile import reconcile_workbook  # noqa: E402

MODEL = ROOT / "model" / "Ferrari_Valuation_Model.xlsx"


@pytest.fixture(scope="module")
def inp():
    return load_inputs(MODEL)


def test_workbook_checks_pass():
    wb = load_workbook(MODEL, data_only=True)
    ws = wb[S.CHECKS]
    results = [ws.cell(r, 3).value for r in range(5, ws.max_row + 1) if isinstance(ws.cell(r, 3).value, bool)]
    assert results and all(results)
    assert wb[S.COVER]["C16"].value == "ALL CHECKS PASS"


def test_python_reconciles_with_saved_workbook():
    df = reconcile_workbook(MODEL)
    assert len(df) > 300
    assert df.passed.all(), df[~df.passed].head()


@pytest.mark.skipif(shutil.which("soffice") is None and shutil.which("libreoffice") is None,
                    reason="LibreOffice not installed")
def test_all_scenarios_reconcile_after_recalculation(tmp_path):
    df = reconcile_workbook(MODEL, all_scenarios=True, workdir=tmp_path)
    assert set(df.scenario) == set(SCENARIOS)
    assert df.passed.all()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_three_statements_tie(inp, scenario):
    p = engine.project(inp, scenario)
    assert np.allclose(p.loc["bs_check"], 0, atol=1e-6)
    assert np.allclose(p.loc["cash_end"], p.loc["cash"])
    assert (p.loc["cash"] >= inp.common["min_cash"] - 1e-6).all()


def test_opening_balance_sheet_matches_workbook(inp):
    bs0 = engine.opening_balance_sheet(inp)
    ws = load_workbook(MODEL, data_only=True)[S.BS]
    col = YEAR_COL[2025]
    for key, label in [("oca", BSL.oca), ("fixed", BSL.fixed), ("dta_other", BSL.dta_other),
                       ("provisions", BSL.provisions), ("other_liab", BSL.other_liab), ("nwc", BSL.nwc)]:
        assert bs0[key] == pytest.approx(ws[f"{col}{find_row(ws, label)}"].value, abs=1e-9)


def test_sensitivity_grid_centre_equals_dcf(inp):
    base = engine.value(inp, "Base")
    grid = sensitivity.wacc_tgr_table(inp, "Base")
    assert grid.iloc[3, 3] == pytest.approx(base.value_per_share, rel=1e-12)
    assert np.all(np.diff(grid.to_numpy(), axis=0) < 0)  # higher WACC -> lower value
    assert np.all(np.diff(grid.to_numpy(), axis=1) > 0)  # higher g -> higher value


def test_scenarios_are_ordered(inp):
    values = [engine.value(inp, sc).value_per_share for sc in SCENARIOS]
    assert values[0] < values[1] < values[2]


def test_base_case_is_anchored_to_company_targets(inp):
    p = engine.project(inp, "Base")
    rev, ebitda = p.loc["revenue"], p.loc["ebitda"]
    assert rev[2026] == pytest.approx(7500, rel=0.01)       # FY2026 guidance ~EUR 7.5bn
    assert ebitda[2026] / rev[2026] >= 0.39                 # FY2026 guidance EBITDA margin >= 39%
    assert rev[2030] == pytest.approx(9000, rel=0.02)       # CMD 2030 target ~EUR 9.0bn
    assert ebitda[2030] >= 3600 and ebitda[2030] / rev[2030] >= 0.40
    assert p.loc["ebit", 2030] / rev[2030] >= 0.30
    assert -p.loc["capex", 2026:2030].sum() == pytest.approx(4700, rel=0.03)  # CMD ~EUR 4.7bn capex 2026-30
