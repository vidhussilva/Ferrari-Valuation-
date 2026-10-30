"""Workbook layout: sheet names, year columns and the row labels Python reads.

Every label the engine reads from (or reconciles against) lives here, so a
renamed row in the workbook fails loudly instead of silently mis-reading.
"""
from openpyxl.utils import get_column_letter

HIST_YEARS = [2023, 2024, 2025]
FCST_YEARS = list(range(2026, 2036))
YEARS = HIST_YEARS + FCST_YEARS
BASE_YEAR = 2025

# Every time-series sheet uses the same year -> column mapping (C = 2023A ... O = 2035E).
YEAR_COL = {y: get_column_letter(3 + i) for i, y in enumerate(YEARS)}
NOTE_COL = get_column_letter(3 + len(YEARS))  # P
VALUE_COL = "C"  # single-value inputs (Assumptions, WACC, DCF valuation block)

SCENARIOS = ("Bear", "Base", "Bull")
SCENARIO_ROW_LABELS = tuple(f"{s} case" for s in SCENARIOS)


class S:
    """Sheet names."""

    COVER = "Cover"
    ASSUMP = "Assumptions"
    HIST = "Historicals"
    REV = "Revenue Build"
    IS = "IS"
    BS = "BS"
    CF = "CF"
    WACC = "WACC"
    DCF = "DCF"
    SENS = "Sensitivity"
    CHECKS = "Checks"


# (key, label, unit) – each block is a "live" row followed by Bear / Base / Bull rows.
SCENARIO_DRIVERS = [
    ("shipments_growth", "Shipments growth", "%"),
    ("price_mix_growth", "Net revenue per car growth (price / mix / personalisation)", "%"),
    ("sponsorship_growth", "Sponsorship, commercial & brand revenue growth", "%"),
    ("gross_margin", "Gross margin", "%"),
    ("capex_pct", "Capex (% of net revenues)", "%"),
]

# (key, label, unit) – one row per driver, shared by all scenarios.
COMMON_DRIVERS = [
    ("other_rev_growth", "Other revenue growth", "%"),
    ("sga_pct", "SG&A (% of net revenues)", "%"),
    ("rnd_pct", "R&D expensed (% of net revenues)", "%"),
    ("other_exp_pct", "Other expenses, net (% of net revenues)", "%"),
    ("da_pct", "D&A (% of net revenues)", "%"),
    ("tax_rate", "Effective tax rate", "%"),
    ("dso", "Trade receivables (days of net revenues)", "days"),
    ("dio", "Inventories (days of cost of revenues)", "days"),
    ("dpo", "Trade payables (days of cost of revenues)", "days"),
    ("oca_pct", "Other current assets (% of net revenues)", "%"),
    ("ol_pct", "Other liabilities incl. customer advances (% of net revenues)", "%"),
    ("int_debt", "Interest rate on gross debt", "%"),
    ("int_cash", "Interest income on cash", "%"),
    ("payout", "Dividend payout (% of prior-year net profit)", "%"),
    ("buyback_target", "Share buyback target", "€m"),
    ("min_cash", "Minimum cash balance", "€m"),
    ("debt_issuance", "Net debt issuance / (repayment)", "€m"),
    ("repurchase_price_growth", "Average repurchase price growth", "%"),
]


class AL:
    """Assumptions sheet single-value labels."""

    scenario = "Active scenario (1 = Bear, 2 = Base, 3 = Bull)"
    scenario_name = "Active scenario name"
    valuation_date = "Valuation date"
    share_price_usd = "Share price - NYSE close at valuation date"
    eurusd = "EUR/USD (ECB reference rate at valuation date)"
    share_price = "Share price at valuation date"
    shares = "Common shares outstanding at valuation date"
    tgr = "Terminal growth rate (perpetuity)"
    mid_year = "Mid-year discounting convention (1 = on, 0 = off)"
    nid = "Net industrial debt at valuation date (reported)"


class WL:
    """WACC sheet labels."""

    rf = "Risk-free rate (10Y German Bund yield)"
    raw_beta = "Raw beta (5Y monthly vs FTSE MIB)"
    blume_weight = "Blume weight on raw beta"
    beta = "Adjusted beta (Blume)"
    erp = "Equity risk premium"
    ke = "Cost of equity (CAPM)"
    kd = "Pre-tax cost of debt"
    tax = "Marginal tax rate (debt tax shield)"
    kd_at = "After-tax cost of debt"
    share_price = "Share price"
    shares = "Shares outstanding"
    mcap = "Market value of equity"
    debt = "Gross debt (31-Dec-2025)"
    capital = "Total capital"
    we = "Equity weight (E / V)"
    wd = "Debt weight (D / V)"
    wacc = "WACC"


class HL:
    """Historicals sheet labels (as reported, € m)."""

    revenue = "Net revenues"
    cogs = "Cost of revenues"
    sga = "Selling, general & administrative costs"
    rnd = "Research & development costs"
    other_exp = "Other expenses, net incl. result from investments (derived)"
    ebit = "EBIT"
    net_fin = "Net financial income / (expenses)"
    pbt = "Profit before taxes"
    tax = "Income tax expense (derived)"
    net_profit = "Net profit"
    da = "Depreciation & amortisation"
    ebitda = "EBITDA"
    eps = "Diluted EPS"
    shipments = "Shipments"
    rev_cars = "Cars and spare parts"
    rev_spons = "Sponsorship, commercial and brand"
    rev_other_reported = "Other - as reported (rounded)"
    rev_other = "Other (derived: total less cars and sponsorship)"
    cash = "Cash and cash equivalents"
    trade_rec = "Trade receivables"
    inventories = "Inventories"
    fin_rec = "Receivables from financing activities"
    oca = "Other current assets incl. current financial assets & tax receivables (derived)"
    ppe = "Property, plant and equipment"
    intangibles = "Intangible assets"
    goodwill = "Goodwill"
    dta = "Deferred tax assets"
    inv_other = "Investments & other financial assets (derived)"
    tnca = "Total non-current assets"
    total_assets = "Total assets"
    trade_pay = "Trade payables"
    other_liab = "Other liabilities"
    tax_pay = "Tax payables"
    provisions = "Provisions"
    emp_benefits = "Employee benefits"
    dtl = "Deferred tax liabilities"
    debt = "Debt"
    ofl = "Other financial liabilities"
    equity = "Total equity"
    tle = "Total equity and liabilities"
    cash_begin = "Cash at beginning of year"
    cfo = "Cash flow from operating activities"
    cfi = "Cash flow used in investing activities"
    cff = "Cash flow used in financing activities"
    dividends = "Dividends paid"
    buybacks = "Share repurchases"
    ifcf = "Industrial free cash flow (reported)"
    nid = "Net industrial debt (reported)"
    capex = "Capital expenditures (reported, approx.)"


class ISL:
    revenue = "Net revenues"
    cogs = "Cost of revenues"
    gross_profit = "Gross profit"
    sga = "SG&A"
    rnd = "Research & development"
    other_exp = "Other expenses, net"
    ebit = "EBIT"
    net_fin = "Net financial income / (expenses)"
    pbt = "Profit before taxes"
    tax = "Income tax expense"
    net_profit = "Net profit"
    da = "Depreciation & amortisation"
    ebitda = "EBITDA"
    avg_shares = "Average shares outstanding"
    eps = "EPS"


class BSL:
    cash = "Cash and cash equivalents"
    trade_rec = "Trade receivables"
    inventories = "Inventories"
    fin_rec = "Receivables from financing activities"
    oca = "Other current assets"
    tca = "Total current assets"
    fixed = "PP&E and intangible assets"
    goodwill = "Goodwill"
    dta_other = "Deferred tax assets & other non-current assets"
    tnca = "Total non-current assets"
    total_assets = "Total assets"
    trade_pay = "Trade payables"
    other_liab = "Other liabilities (incl. customer advances & tax payables)"
    provisions = "Provisions & employee benefits"
    dtl = "Deferred tax liabilities"
    debt = "Debt"
    ofl = "Other financial liabilities"
    total_liab = "Total liabilities"
    equity = "Total equity"
    tle = "Total liabilities & equity"
    check = "Balance check (assets - liabilities - equity)"
    nwc = "Net working capital"
    net_debt = "Net debt / (net cash)"
    shares = "Shares outstanding (period end)"
    rep_price = "Average repurchase price"


class CFL:
    net_profit = "Net profit"
    da = "Depreciation & amortisation"
    wc = "Change in net working capital & other"
    cfo = "Cash flow from operating activities"
    capex = "Capital expenditures"
    cfi = "Cash flow from investing activities"
    dividends = "Dividends paid"
    buybacks = "Share repurchases"
    debt_other = "Net debt issuance / (repayment) & other"
    cff = "Cash flow from financing activities"
    fx = "FX translation & other"
    net_change = "Net change in cash"
    cash_begin = "Cash at beginning of year"
    cash_end = "Cash at end of year"
    fcf = "Free cash flow (CFO + CFI)"


class DL:
    """DCF sheet labels."""

    t = "Year index"
    period = "Discount period (years)"
    revenue = "Net revenues"
    ebitda = "EBITDA"
    ebit = "EBIT"
    tax = "Less: taxes on EBIT"
    nopat = "NOPAT"
    da = "Plus: D&A"
    capex = "Less: capital expenditures"
    nwc = "Less: increase in net working capital"
    ufcf = "Unlevered free cash flow"
    df = "Discount factor"
    pv = "PV of unlevered free cash flow"
    wacc = "WACC"
    tgr = "Terminal growth rate"
    sum_pv = "Sum of PV of free cash flows (2026E-2035E)"
    tv = "Terminal value at end-2035 (Gordon growth)"
    pv_tv = "PV of terminal value"
    ev = "Enterprise value"
    tv_pct = "PV of terminal value as % of EV"
    tv_mult = "Implied terminal EV / EBITDA (2035E)"
    nid = "Less: net industrial debt"
    equity = "Equity value"
    shares = "Shares outstanding (m)"
    value_ps = "Implied value per share"
    price = "Share price at valuation date"
    upside = "Implied upside / (downside)"
