"""Independent Python (pandas / NumPy) implementation of the Excel model.

The engine reads only the workbook's literal inputs (excel_io.load_inputs) and rebuilds
the revenue build, three statements, WACC and DCF from first principles. Matching the
workbook to floating-point precision is the reconciliation test.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .excel_io import ModelInputs
from .layout import BASE_YEAR, FCST_YEARS, SCENARIOS


def drivers(inp: ModelInputs, scenario: str | int | None = None, shocks: dict | None = None) -> pd.DataFrame:
    """Driver table (rows = forecast years) for a scenario, with optional additive shocks."""
    if scenario is None:
        scenario = inp.scenario
    if isinstance(scenario, int):
        scenario = SCENARIOS[scenario - 1]
    table = {k: v[scenario].copy() for k, v in inp.scenario_drivers.items()}
    table.update({k: v.copy() for k, v in inp.common.items()})
    df = pd.DataFrame(table, index=FCST_YEARS)
    for key, delta in (shocks or {}).items():
        df[key] = df[key] + delta
    return df


def opening_balance_sheet(inp: ModelInputs) -> dict:
    """FY2025A condensed balance sheet, derived from the reported lines the same way the workbook does."""
    h = {k: v.get(BASE_YEAR) for k, v in inp.hist.items()}
    oca = h["total_assets"] - h["tnca"] - h["inventories"] - h["trade_rec"] - h["fin_rec"] - h["cash"]
    emp_benefits = (h["total_assets"] - h["equity"] - h["trade_pay"] - h["other_liab"] - h["tax_pay"]
                    - h["provisions"] - h["dtl"] - h["debt"] - h["ofl"])
    bs = {
        "cash": h["cash"], "trade_rec": h["trade_rec"], "inventories": h["inventories"], "fin_rec": h["fin_rec"],
        "oca": oca, "fixed": h["ppe"] + h["intangibles"], "goodwill": h["goodwill"],
        "dta_other": h["tnca"] - h["goodwill"] - h["intangibles"] - h["ppe"],
        "trade_pay": h["trade_pay"], "other_liab": h["other_liab"] + h["tax_pay"],
        "provisions": h["provisions"] + emp_benefits, "dtl": h["dtl"], "debt": h["debt"], "ofl": h["ofl"],
        "equity": h["equity"],
    }
    bs["nwc"] = bs["trade_rec"] + bs["inventories"] + bs["oca"] - bs["trade_pay"] - bs["other_liab"]
    return bs


def project(inp: ModelInputs, scenario=None, shocks: dict | None = None) -> pd.DataFrame:
    """Three-statement projection for 2026E-2035E. Returns line items (rows) x years (columns)."""
    d = drivers(inp, scenario, shocks)
    h = inp.hist
    bs0 = opening_balance_sheet(inp)

    ship = h["shipments"][BASE_YEAR]
    rpc = h["rev_cars"][BASE_YEAR] / ship * 1000
    spons = h["rev_spons"][BASE_YEAR]
    other = h["revenue"][BASE_YEAR] - h["rev_cars"][BASE_YEAR] - h["rev_spons"][BASE_YEAR]
    prev = dict(bs0, net_profit=h["net_profit"][BASE_YEAR], shares=inp.shares, rep_price=inp.share_price)

    rows = []
    for y in FCST_YEARS:
        x = d.loc[y]
        ship *= 1 + x.shipments_growth
        rpc *= 1 + x.price_mix_growth
        spons *= 1 + x.sponsorship_growth
        other *= 1 + x.other_rev_growth
        cars = ship * rpc / 1000
        rev = cars + spons + other

        cogs = -rev * (1 - x.gross_margin)
        gross_profit = rev + cogs
        ebit = gross_profit - rev * x.sga_pct - rev * x.rnd_pct - rev * x.other_exp_pct
        da = rev * x.da_pct
        net_fin = -x.int_debt * prev["debt"] + x.int_cash * prev["cash"]
        pbt = ebit + net_fin
        tax = -pbt * x.tax_rate
        net_profit = pbt + tax

        trade_rec = rev * x.dso / 365
        inventories = -cogs * x.dio / 365
        oca = rev * x.oca_pct
        trade_pay = -cogs * x.dpo / 365
        other_liab = rev * x.ol_pct
        nwc = trade_rec + inventories + oca - trade_pay - other_liab

        wc = -(nwc - prev["nwc"])
        cfo = net_profit + da + wc
        capex = -rev * x.capex_pct
        dividends = -x.payout * prev["net_profit"]
        cash_avail = prev["cash"] + cfo + capex + dividends + x.debt_issuance - x.min_cash
        buybacks = -max(0.0, min(x.buyback_target, cash_avail))
        cff = dividends + buybacks + x.debt_issuance
        cash = prev["cash"] + cfo + capex + cff

        debt = prev["debt"] + x.debt_issuance
        fixed = prev["fixed"] - capex - da
        equity = prev["equity"] + net_profit + dividends + buybacks
        total_assets = (cash + trade_rec + inventories + bs0["fin_rec"] + oca + fixed + bs0["goodwill"]
                        + bs0["dta_other"])
        total_liab = trade_pay + other_liab + bs0["provisions"] + bs0["dtl"] + debt + bs0["ofl"]

        rep_price = prev["rep_price"] * (1 + x.repurchase_price_growth)
        shares = prev["shares"] + buybacks / rep_price
        eps = net_profit / ((prev["shares"] + shares) / 2)

        nopat = ebit * (1 - x.tax_rate)
        ufcf = nopat + da + capex + wc

        rows.append(dict(
            shipments=ship, rev_per_car=rpc, rev_cars=cars, rev_sponsorship=spons, rev_other=other, revenue=rev,
            cogs=cogs, gross_profit=gross_profit, ebit=ebit, da=da, ebitda=ebit + da, net_fin=net_fin, pbt=pbt,
            tax=tax, net_profit=net_profit, eps=eps, cash=cash, trade_rec=trade_rec, inventories=inventories,
            oca=oca, fixed=fixed, total_assets=total_assets, trade_pay=trade_pay, other_liab=other_liab, debt=debt,
            equity=equity, total_liab=total_liab, bs_check=round(total_assets - total_liab - equity, 6), nwc=nwc,
            shares=shares, cfo=cfo, wc=wc, capex=capex, dividends=dividends, buybacks=buybacks, cash_end=cash,
            nopat=nopat, ufcf=ufcf,
        ))
        prev = dict(prev, cash=cash, debt=debt, fixed=fixed, equity=equity, nwc=nwc, net_profit=net_profit,
                    shares=shares, rep_price=rep_price)
    return pd.DataFrame(rows, index=FCST_YEARS).T


def cost_of_capital(inp: ModelInputs, **overrides) -> dict:
    p = dict(inp.wacc, **overrides)
    beta = p["raw_beta"] * p["blume_weight"] + (1 - p["blume_weight"])
    ke = p["rf"] + beta * p["erp"]
    kd_at = p["kd"] * (1 - p["tax"])
    mcap = inp.share_price * inp.shares
    debt = inp.hist["debt"][BASE_YEAR]
    we, wd = mcap / (mcap + debt), debt / (mcap + debt)
    return dict(beta=beta, ke=ke, kd_after_tax=kd_at, market_cap=mcap, we=we, wd=wd, wacc=we * ke + wd * kd_at)


def discount_periods(inp: ModelInputs) -> np.ndarray:
    t = np.arange(1, len(FCST_YEARS) + 1, dtype=float)
    return t - 0.5 * inp.mid_year


def dcf_grid(ufcf: np.ndarray, periods: np.ndarray, waccs, tgrs, nid: float, shares: float):
    """Vectorised DCF over every (WACC, g) pair. Returns (value per share, EV) arrays shaped (len(waccs), len(tgrs))."""
    w = np.asarray(waccs, dtype=float)[:, None]
    g = np.asarray(tgrs, dtype=float)[None, :]
    n = len(ufcf)
    pv_fcf = (ufcf[None, :] * (1 + w) ** -periods[None, :]).sum(axis=1, keepdims=True)
    pv_tv = ufcf[-1] * (1 + g) / (w - g) * (1 + w) ** -n
    ev = pv_fcf + pv_tv
    return (ev - nid) / shares, ev


def exit_multiple_grid(ufcf: np.ndarray, terminal_ebitda: float, periods: np.ndarray, waccs, multiples,
                       nid: float, shares: float):
    """Vectorised DCF with an exit-multiple terminal value (EV / final-year EBITDA, discounted from the end of the
    forecast). Returns (value per share, EV) arrays shaped (len(waccs), len(multiples))."""
    w = np.asarray(waccs, dtype=float)[:, None]
    m = np.asarray(multiples, dtype=float)[None, :]
    n = len(ufcf)
    pv_fcf = (ufcf[None, :] * (1 + w) ** -periods[None, :]).sum(axis=1, keepdims=True)
    ev = pv_fcf + m * terminal_ebitda * (1 + w) ** -n
    return (ev - nid) / shares, ev


@dataclass
class Valuation:
    projection: pd.DataFrame
    wacc: dict
    tgr: float
    discount_factor: np.ndarray
    pv_ufcf: np.ndarray
    sum_pv: float
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    equity_value: float
    value_per_share: float
    share_price: float
    base_revenue: float  # FY2025A, for growth statistics

    @property
    def upside(self) -> float:
        return self.value_per_share / self.share_price - 1

    def summary(self) -> dict:
        p = self.projection
        return {
            "wacc": self.wacc["wacc"], "ke": self.wacc["ke"], "beta": self.wacc["beta"],
            "kd_after_tax": self.wacc["kd_after_tax"], "tgr": self.tgr, "sum_pv": self.sum_pv,
            "terminal_value": self.terminal_value, "pv_terminal_value": self.pv_terminal_value,
            "enterprise_value": self.enterprise_value, "tv_pct_of_ev": self.pv_terminal_value / self.enterprise_value,
            "equity_value": self.equity_value, "value_per_share": self.value_per_share, "upside": self.upside,
            "revenue_2030E": p.loc["revenue", 2030], "ebitda_margin_2030E": p.loc["ebitda", 2030] / p.loc["revenue", 2030],
            "ebit_margin_2030E": p.loc["ebit", 2030] / p.loc["revenue", 2030],
            "revenue_cagr_25_35": (p.loc["revenue", 2035] / self.base_revenue) ** (1 / 10) - 1,
            "cum_ufcf_26_30": p.loc["ufcf", 2026:2030].sum(), "eps_2030E": p.loc["eps", 2030],
        }


def value(inp: ModelInputs, scenario=None, shocks: dict | None = None, wacc: float | None = None,
          tgr: float | None = None, wacc_overrides: dict | None = None) -> Valuation:
    proj = project(inp, scenario, shocks)
    coc = cost_of_capital(inp, **(wacc_overrides or {}))
    if wacc is not None:
        coc = dict(coc, wacc=wacc)
    w, g = coc["wacc"], inp.tgr if tgr is None else tgr
    if w <= g:
        raise ValueError(f"WACC ({w:.2%}) must exceed terminal growth ({g:.2%})")
    ufcf = proj.loc["ufcf"].to_numpy(dtype=float)
    df = (1 + w) ** -discount_periods(inp)
    pv = ufcf * df
    tv = ufcf[-1] * (1 + g) / (w - g)
    pv_tv = tv * (1 + w) ** -len(ufcf)
    ev = pv.sum() + pv_tv
    equity = ev - inp.nid
    return Valuation(projection=proj, wacc=coc, tgr=g, discount_factor=df, pv_ufcf=pv, sum_pv=pv.sum(),
                     terminal_value=tv, pv_terminal_value=pv_tv, enterprise_value=ev, equity_value=equity,
                     value_per_share=equity / inp.shares, share_price=inp.share_price,
                     base_revenue=inp.hist["revenue"][BASE_YEAR])
