#!/usr/bin/env python3
"""Reconcile the Python engine with the Excel model, line by line.

By default it reads the cached values saved in the workbook (the scenario it was last
calculated under). --all-scenarios recalculates the workbook under Bear, Base and Bull
with headless LibreOffice and reconciles all three.

    python scripts/reconcile_with_excel.py [--model PATH] [--recalc | --all-scenarios] [--out outputs]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ferrari_valuation.reconcile import reconcile_workbook, write_report  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, default=ROOT / "model" / "Ferrari_Valuation_Model.xlsx")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--recalc", action="store_true", help="recalculate with LibreOffice before reading")
    group.add_argument("--all-scenarios", action="store_true", help="recalculate and reconcile Bear, Base and Bull")
    args = parser.parse_args(argv)

    df = reconcile_workbook(args.model, all_scenarios=args.all_scenarios, recalc=args.recalc,
                            workdir=args.out / "recalculated")
    report = write_report(df, args.out, args.model.relative_to(ROOT) if args.model.is_relative_to(ROOT) else args.model)
    for sc, g in df.groupby("scenario", sort=False):
        print(f"{sc:<5} {len(g):>4} comparisons  max |diff| {g.abs_diff.max():.2e}  "
              f"{'PASS' if g.passed.all() else 'FAIL'}")
    print(f"Report: {report}")
    return 0 if df.passed.all() else 1


if __name__ == "__main__":
    sys.exit(main())
