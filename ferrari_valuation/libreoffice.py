"""Headless LibreOffice recalculation, so the workbook can be re-scored without Excel.

Switching the scenario selector and re-saving through openpyxl drops the workbook's cached
results. Converting the file with LibreOffice evaluates every formula and stores the results,
which is what excel_io.read_outputs reads.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from openpyxl import load_workbook

from .excel_io import find_row
from .layout import AL, S, VALUE_COL

MAC_SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"


def find_soffice() -> str:
    for candidate in (os.environ.get("SOFFICE"), shutil.which("soffice"), shutil.which("libreoffice"), MAC_SOFFICE):
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError("LibreOffice (soffice) not found. Install it, set SOFFICE=/path/to/soffice, "
                            "or open and save the workbook in Excel instead.")


def recalculate(src: str | Path, out_dir: str | Path, scenario: int | None = None, timeout: int = 180) -> Path:
    """Copy `src` (optionally switching the scenario selector), recalculate it, and return the new path."""
    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ferrari_recalc_") as tmp:
        # Re-saving through openpyxl drops every cached value, which forces LibreOffice to evaluate all formulas.
        wb = load_workbook(src)
        if scenario is not None:
            ws = wb[S.ASSUMP]
            ws[f"{VALUE_COL}{find_row(ws, AL.scenario)}"] = int(scenario)
        stem = src.stem if scenario is None else f"{src.stem}_scenario{scenario}"
        staged = Path(tmp) / f"{stem}.xlsx"
        wb.save(staged)
        profile = Path(tmp) / "lo_profile"
        cmd = [find_soffice(), "--headless", f"-env:UserInstallation={profile.as_uri()}",
               "--convert-to", "xlsx", "--outdir", str(out_dir), str(staged)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = out_dir / staged.name
        if result.returncode != 0 or not out.exists():
            raise RuntimeError(f"LibreOffice recalculation failed: {result.stderr.strip() or result.stdout.strip()}")
    return out
