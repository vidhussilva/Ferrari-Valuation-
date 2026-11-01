#!/usr/bin/env python3
"""Automated sensitivity analysis driven by the Excel model's inputs.

Reads every assumption from the workbook, re-runs the model in Python for each case and
writes CSVs, an Excel results file and PNG charts to outputs/.

    python scripts/run_sensitivity.py [--model model/Ferrari_Valuation_Model.xlsx] [--out outputs]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ferrari_valuation import charts, sensitivity  # noqa: E402
from ferrari_valuation.excel_io import load_inputs  # noqa: E402
from ferrari_valuation.layout import SCENARIOS  # noqa: E402


def pct_labels(df):
    out = df.copy()
    out.index = [f"{v:.2%}" for v in df.index]
    out.columns = [f"{v:.2%}" for v in df.columns]
    out.index.name, out.columns.name = df.index.name, df.columns.name
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, default=ROOT / "model" / "Ferrari_Valuation_Model.xlsx")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs")
    args = parser.parse_args(argv)

    inp = load_inputs(args.model)
    res = sensitivity.run_all(inp)
    out, chart_dir = args.out, args.out / "charts"
    out.mkdir(parents=True, exist_ok=True)

    summary = res["scenario_summary"]
    summary.to_csv(out / "scenario_summary.csv")
    for sc, table in res["wacc_g_value_per_share"].items():
        pct_labels(table).to_csv(out / f"sensitivity_wacc_g_{sc.lower()}.csv", float_format="%.2f")
    res["tornado"].to_csv(out / "tornado_base.csv", index=False, float_format="%.2f")
    pct_labels(res["growth_margin"]).to_csv(out / "sensitivity_growth_margin_base.csv", float_format="%.2f")
    res["projections"].to_csv(out / "scenario_projections.csv", index=False, float_format="%.4f")
    res["reverse_dcf"].to_csv(out / "reverse_dcf.csv", index=False, float_format="%.6f")

    with pd.ExcelWriter(out / "python_sensitivity_results.xlsx") as xw:
        summary.to_excel(xw, sheet_name="Scenario summary")
        for sc, table in res["wacc_g_value_per_share"].items():
            pct_labels(table).to_excel(xw, sheet_name=f"WACC x g ({sc})")
        pct_labels(res["wacc_g_enterprise_value"]).to_excel(xw, sheet_name="WACC x g EV (Base)")
        res["tornado"].to_excel(xw, sheet_name="Tornado (Base)", index=False)
        pct_labels(res["growth_margin"]).to_excel(xw, sheet_name="Growth x margin (Base)")
        res["projections"].to_excel(xw, sheet_name="Projections", index=False)
        res["reverse_dcf"].to_excel(xw, sheet_name="Reverse DCF (Base)", index=False)

    charts.wacc_tgr_heatmap(res["wacc_g_value_per_share"]["Base"], inp.share_price, chart_dir / "wacc_g_heatmap.png")
    charts.tornado_chart(res["tornado"], chart_dir / "tornado.png")
    charts.scenario_bars(summary, inp.share_price, chart_dir / "scenario_values.png")
    charts.projection_panels(res["projections"], chart_dir / "scenario_projections.png")

    print(f"Share price at valuation date: EUR {inp.share_price:,.2f}")
    for sc in SCENARIOS:
        s = summary[sc]
        print(f"  {sc:<5} value/share EUR {s.value_per_share:8.2f}  ({s.upside:+.1%})  EV EUR {s.enterprise_value:,.0f}m  "
              f"WACC {s.wacc:.2%}  2030E revenue EUR {s.revenue_2030E:,.0f}m  EBITDA margin {s.ebitda_margin_2030E:.1%}")
    pw = summary.loc["value_per_share", "Probability-weighted"]
    print(f"  Probability-weighted (25/50/25): EUR {pw:,.2f} ({pw / inp.share_price - 1:+.1%})")
    t = res["tornado"].iloc[0]
    print(f"  Largest single driver: {t.driver} (EUR {min(t.value_at_low_input, t.value_at_high_input):,.0f}"
          f" - {max(t.value_at_low_input, t.value_at_high_input):,.0f})")
    print(f"  Priced in at EUR {inp.share_price:,.2f} (one lever at a time): " + "; ".join(
        f"{r.lever} {r.implied_level:.2%} (base {r.base_level:.2%})" for r in res["reverse_dcf"].itertuples()))
    print(f"Outputs written to {out}")


if __name__ == "__main__":
    main()
