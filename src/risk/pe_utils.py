"""
pe_utils.py
===========
PE fund performance metrics and risk utilities.

Functions
---------
xirr(cash_flows, dates, guess)
    Extended IRR for irregular cash flows.

fund_irr(engine, fund_id, as_of_date, fee_rate, carry_rate)
    Gross and net IRR for a PE fund.

pe_multiples(engine, fund_id, as_of_date)
    DPI, RVPI, TVPI at fund level.

pe_multiples_by_company(engine, fund_id, as_of_date)
    DPI, RVPI, TVPI per portfolio company.

pe_multiples_timeseries(engine, fund_id)
    Quarterly TVPI evolution over fund life.

pme_long_nickels(cash_flows, dates, index_prices, terminal_nav, valuation_date)
    Long-Nickels PME: PE IRR vs public market equivalent IRR and alpha.

Regulatory basis
----------------
IPEV Valuation Guidelines (International Private Equity Valuation)
ILPA reporting standards
AIFMD Art. 19 (independent valuation)
EU231/2013 Articles 46-49 (risk management)
"""

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Session

from src.data.database import (
    PEFund, PEPortfolioCompany, PEFundInvestment,
    PECashFlow, PENavHistory, PEValuationReport
)


__all__ = [
    'xirr',
    'fund_irr',
    'pe_multiples',
    'pe_multiples_by_company',
    'pe_multiples_timeseries',
    'pe_value_bridge',
    'pme_long_nickels',
]


def xirr(
    cash_flows: list,
    dates: list,
    guess: float = 0.10
) -> Optional[float]:
    """
    Extended Internal Rate of Return for irregular cash flows.
    Finds rate r such that NPV of all cash flows equals zero.

    $$\\sum_{i=0}^{n} \\frac{CF_i}{(1+r)^{d_i/365}} = 0$$

    Parameters
    ----------
    cash_flows : list of float
        Cash flows. Negative = outflows (capital calls).
        Positive = inflows (distributions, exit proceeds).
    dates : list of str or datetime
        Dates corresponding to each cash flow.
    guess : float
        Initial guess for IRR. Default 0.10 (10%).

    Returns
    -------
    float or None
        IRR as decimal (e.g. 0.20 = 20%).
        Returns None if no solution found.

    Examples
    --------
    >>> cfs   = [-100, 50, 80]
    >>> dates = ['2018-01-01', '2021-01-01', '2023-01-01']
    >>> irr   = xirr(cfs, dates)
    """
    dates = pd.to_datetime(dates)
    d0    = dates[0]
    days  = [(d - d0).days for d in dates]
    cfs   = np.array(cash_flows, dtype=float)

    def npv(r):
        return sum(cf / (1 + r) ** (d / 365)
                   for cf, d in zip(cfs, days))

    try:
        return float(brentq(npv, -0.999, 100.0, maxiter=1000))
    except (ValueError, RuntimeError):
        return None


def fund_irr(
    engine: sa.Engine,
    fund_id: str,
    as_of_date: str,
    fee_rate: float = 0.02,
    carry_rate: float = 0.20,
) -> dict:
    """
    Compute gross and net IRR for a PE fund.

    Gross IRR: based on raw cash flows plus terminal NAV.
    Net IRR: after management fees (fee_rate) and carried interest (carry_rate).

    Parameters
    ----------
    engine : sa.Engine
    fund_id : str
    as_of_date : str
        Valuation date. Terminal NAV added as final cash flow.
    fee_rate : float
        Annual management fee. Default 0.02 (2%).
    carry_rate : float
        Carried interest. Default 0.20 (20%).

    Returns
    -------
    dict with keys:
        gross_irr, net_irr, cash_flows, dates
    """
    with Session(engine) as session:
        cfs = session.query(PECashFlow).filter(
            PECashFlow.fund_id == fund_id,
            PECashFlow.date   <= as_of_date
        ).order_by(PECashFlow.date).all()

        nav = session.query(PENavHistory).filter(
            PENavHistory.fund_id    == fund_id,
            PENavHistory.company_id == None,
            PENavHistory.date       <= as_of_date
        ).order_by(PENavHistory.date.desc()).first()

    cf_amounts = [cf.amount_eur for cf in cfs]
    cf_dates   = [cf.date for cf in cfs]

    if nav:
        cf_amounts.append(nav.nav_eur)
        cf_dates.append(as_of_date)

    gross_irr = xirr(cf_amounts, cf_dates)

    # net IRR: approximate fee and carry deduction
    paid_in       = abs(sum(a for a in cf_amounts if a < 0))
    distributions = sum(a for a in cf_amounts if a > 0)
    fees          = paid_in * fee_rate
    profit        = max(0, distributions - paid_in)
    carry         = profit * carry_rate
    n_positive    = max(1, sum(1 for a in cf_amounts if a > 0))
    net_cf        = [
        a - fees / max(1, sum(1 for x in cf_amounts if x < 0)) if a < 0
        else a - carry / n_positive
        for a in cf_amounts
    ]
    net_irr = xirr(net_cf, cf_dates)

    return {
        'gross_irr'  : gross_irr,
        'net_irr'    : net_irr,
        'cash_flows' : cf_amounts,
        'dates'      : cf_dates,
    }


def pe_multiples(
    engine: sa.Engine,
    fund_id: str,
    as_of_date: str,
) -> dict:
    """
    Compute DPI, RVPI and TVPI for a PE fund.

    DPI  = Total distributions / Paid-in capital
    RVPI = Residual NAV / Paid-in capital
    TVPI = DPI + RVPI

    Parameters
    ----------
    engine : sa.Engine
    fund_id : str
    as_of_date : str

    Returns
    -------
    dict with keys:
        dpi, rvpi, tvpi, paid_in, distributions, nav
    """
    with Session(engine) as session:
        cfs = session.query(PECashFlow).filter(
            PECashFlow.fund_id == fund_id,
            PECashFlow.date   <= as_of_date
        ).all()

        nav = session.query(PENavHistory).filter(
            PENavHistory.fund_id    == fund_id,
            PENavHistory.company_id == None,
            PENavHistory.date       <= as_of_date
        ).order_by(PENavHistory.date.desc()).first()

    paid_in       = abs(sum(cf.amount_eur for cf in cfs if cf.amount_eur < 0))
    distributions = sum(cf.amount_eur for cf in cfs if cf.amount_eur > 0)
    nav_eur       = nav.nav_eur if nav else 0.0

    dpi  = distributions / paid_in if paid_in > 0 else 0.0
    rvpi = nav_eur / paid_in       if paid_in > 0 else 0.0
    tvpi = dpi + rvpi

    return {
        'dpi'          : round(dpi, 3),
        'rvpi'         : round(rvpi, 3),
        'tvpi'         : round(tvpi, 3),
        'paid_in'      : round(paid_in, 2),
        'distributions': round(distributions, 2),
        'nav'          : round(nav_eur, 2),
    }


def pe_multiples_by_company(
    engine: sa.Engine,
    fund_id: str,
    as_of_date: str,
) -> pd.DataFrame:
    """
    Compute DPI, RVPI and TVPI per portfolio company.

    Returns
    -------
    pd.DataFrame with columns:
        company_id, company_name, cost_basis, distributions,
        nav, dpi, rvpi, tvpi, status
    """
    with Session(engine) as session:
        investments = session.query(PEFundInvestment).filter_by(
            fund_id=fund_id).all()
        companies   = {c.company_id: c.company_name
                       for c in session.query(PEPortfolioCompany).all()}
        cfs         = session.query(PECashFlow).filter(
            PECashFlow.fund_id    == fund_id,
            PECashFlow.date       <= as_of_date,
            PECashFlow.company_id != None
        ).all()
        navs        = session.query(PENavHistory).filter(
            PENavHistory.fund_id    == fund_id,
            PENavHistory.date       <= as_of_date,
            PENavHistory.company_id != None
        ).all()

    nav_map = {}
    for n in sorted(navs, key=lambda x: x.date):
        nav_map[n.company_id] = n.nav_eur

    dist_map = {}
    for cf in cfs:
        if cf.amount_eur > 0 and cf.company_id:
            dist_map[cf.company_id] = dist_map.get(cf.company_id, 0) + cf.amount_eur

    rows = []
    for inv in investments:
        cid          = inv.company_id
        cost         = inv.cost_basis_eur
        distributions= dist_map.get(cid, 0)
        nav_eur      = nav_map.get(cid, 0) if inv.exit_date is None else 0
        dpi          = distributions / cost if cost > 0 else 0
        rvpi         = nav_eur / cost       if cost > 0 else 0
        tvpi         = dpi + rvpi
        rows.append({
            'company_id'   : cid,
            'company_name' : companies.get(cid, cid),
            'cost_basis'   : cost,
            'distributions': distributions,
            'nav'          : nav_eur,
            'dpi'          : round(dpi, 3),
            'rvpi'         : round(rvpi, 3),
            'tvpi'         : round(tvpi, 3),
            'status'       : 'Exited' if inv.exit_date else 'Active',
        })

    return pd.DataFrame(rows)


def pe_multiples_timeseries(
    engine: sa.Engine,
    fund_id: str,
) -> pd.DataFrame:
    """
    Quarterly TVPI evolution over fund life.

    Returns
    -------
    pd.DataFrame with columns: date, paid_in, dpi, rvpi, tvpi
    """
    with Session(engine) as session:
        cfs  = session.query(PECashFlow).filter_by(fund_id=fund_id).all()
        navs = session.query(PENavHistory).filter(
            PENavHistory.fund_id    == fund_id,
            PENavHistory.company_id == None
        ).order_by(PENavHistory.date).all()

    rows = []
    for nav in navs:
        date          = nav.date
        paid_in       = abs(sum(cf.amount_eur for cf in cfs
                               if cf.amount_eur < 0 and cf.date <= date))
        distributions = sum(cf.amount_eur for cf in cfs
                            if cf.amount_eur > 0 and cf.date <= date)
        nav_eur       = nav.nav_eur
        dpi           = distributions / paid_in if paid_in > 0 else 0
        rvpi          = nav_eur / paid_in       if paid_in > 0 else 0
        rows.append({
            'date'   : pd.Timestamp(date),
            'paid_in': paid_in,
            'dpi'    : round(dpi, 3),
            'rvpi'   : round(rvpi, 3),
            'tvpi'   : round(dpi + rvpi, 3),
        })

    return pd.DataFrame(rows)


def pme_long_nickels(
    cash_flows: list,
    dates: list,
    index_prices: pd.Series,
    terminal_nav: float = 0.0,
    valuation_date: str = None,
) -> dict:
    """
    Long-Nickels Public Market Equivalent (PME) analysis.

    Replicates the PE fund's capital call and distribution schedule by
    buying/selling a public index at the same dates and amounts. Compares
    the resulting index portfolio value (PME terminal NAV) to the PE fund
    NAV to determine whether public markets outperformed PE.

    Algorithm
    ---------
    For each capital call (cf < 0): buy |cf| / price index units.
    For each distribution (cf > 0): sell cf / price index units
        (floored at zero — cannot sell more units than held).
    PME terminal NAV = remaining units × index price at valuation_date.

    If PME IRR > PE IRR: public markets outperformed (negative alpha).
    If PE IRR > PME IRR: PE outperformed (positive alpha).

    Parameters
    ----------
    cash_flows : list of float
        PE cash flows. Negative = capital calls. Positive = distributions.
    dates : list of str or datetime
        Dates corresponding to each cash flow.
    index_prices : pd.Series
        Daily index prices with DatetimeIndex. Nearest prior price used
        via .asof() for each cash flow date.
    terminal_nav : float
        Current PE fund NAV. Added at valuation_date to compute PE IRR.
        Default 0.0 (fully realised fund).
    valuation_date : str or None
        Terminal date for NAV and PME computations. If None, uses the
        last date in dates.

    Returns
    -------
    dict with keys:
        pme_multiple     float — (distributions + PME NAV) / paid-in capital
        pme_irr          float or None
        pe_irr           float or None — computed from cash_flows + terminal_nav
        alpha            float or None — PE IRR minus PME IRR
        pme_terminal_nav float — simulated index portfolio value at valuation_date
        units            float — index units held at termination
        simulated_nav    pd.Series — index portfolio value after each cash flow
    """
    dates_pd  = pd.to_datetime(dates)
    term_date = pd.Timestamp(valuation_date) if valuation_date else dates_pd[-1]
    prices    = index_prices.sort_index()

    units      = 0.0
    nav_points = {}

    for cf, date in zip(cash_flows, dates_pd):
        price = float(prices.asof(date))
        if np.isnan(price) or price <= 0:
            continue
        if cf < 0:
            units += abs(cf) / price
        else:
            units = max(0.0, units - cf / price)
        nav_points[date] = units * price

    term_price       = float(prices.asof(term_date))
    pme_terminal_nav = units * term_price if not np.isnan(term_price) else 0.0

    paid_in       = sum(abs(cf) for cf in cash_flows if cf < 0)
    distributions = sum(cf for cf in cash_flows if cf > 0)

    pme_multiple = (
        (distributions + pme_terminal_nav) / paid_in if paid_in > 0 else float('nan')
    )

    terminal_dates = list(dates_pd) + [term_date]
    pme_irr = xirr(list(cash_flows) + [pme_terminal_nav], terminal_dates)
    pe_irr  = xirr(list(cash_flows) + [terminal_nav],     terminal_dates)

    alpha = (
        pe_irr - pme_irr
        if pe_irr is not None and pme_irr is not None
        else None
    )

    return {
        'pme_multiple'    : round(pme_multiple, 3) if not np.isnan(pme_multiple) else None,
        'pme_irr'         : pme_irr,
        'pe_irr'          : pe_irr,
        'alpha'           : alpha,
        'pme_terminal_nav': round(pme_terminal_nav, 2),
        'units'           : units,
        'simulated_nav'   : pd.Series(nav_points),
    }


def pe_value_bridge(
    engine: sa.Engine,
    fund_id: str,
    company_id: Optional[str] = None,
    ) -> dict:
    """
    PE return attribution: value bridge decomposition.

    Decomposes total equity value created into four sources:
    EBITDA growth, multiple expansion, leverage effect, and
    interim distributions.

    Regulatory context
    ------------------
    AIFMD Annex IV and CSSF circular 18/698 expect performance
    attribution that distinguishes operational value creation from
    financial engineering. The value bridge is the standard LP
    reporting methodology (ILPA guidelines) and is consistent with
    CSSF expectations for the internal governance report (MRS-37).

    Attribution formulas
    --------------------

    For exited companies all inputs are realised. Gap should be near zero.
    For active companies inputs are current appraiser values from
    pe_valuation_report. Attribution is partially unrealised. Gap may be
    non-zero due to DCF assumptions, minority discounts, and other
    appraiser inputs outside the EV/EBITDA bridge. Shown, not suppressed.

    Parameters
    ----------
    engine : sa.Engine
    fund_id : str
    company_id : str or None
        If None, returns aggregation across all companies in the fund.

    Returns
    -------
    dict with keys:
        fund_id         str
        company_id      str or None
        rows            list[dict]  one per company
        fund_totals     dict        summed EUR and % of total value created
    """
    GAP_THRESHOLD = 0.05

    with Session(engine) as session:

        inv_query = session.query(PEFundInvestment).filter(
            PEFundInvestment.fund_id == fund_id
        )
        if company_id is not None:
            inv_query = inv_query.filter(
                PEFundInvestment.company_id == company_id
            )
        investments = inv_query.all()

        if not investments:
            raise ValueError(
                f"No investments found for fund_id={fund_id}"
                + (f", company_id={company_id}" if company_id else "")
            )

        company_ids = [inv.company_id for inv in investments]

        companies = {
            c.company_id: c.company_name
            for c in session.query(PEPortfolioCompany).filter(
                PEPortfolioCompany.company_id.in_(company_ids)
            ).all()
        }

        # All valuation reports for these companies in this fund
        all_vr = session.query(PEValuationReport).filter(
            PEValuationReport.fund_id    == fund_id,
            PEValuationReport.company_id.in_(company_ids)
        ).order_by(PEValuationReport.date).all()

        # Interim distributions only — exit proceeds are captured in
        # exit_price_eur and must not be double-counted here
        all_cf = session.query(PECashFlow).filter(
            PECashFlow.fund_id    == fund_id,
            PECashFlow.company_id.in_(company_ids),
            PECashFlow.flow_type  == 'distribution'
        ).all()

    # Build per-company valuation maps
    entry_vr_map = {}   # company_id -> earliest valuation report
    exit_vr_map  = {}   # company_id -> latest valuation report
    for vr in all_vr:
        cid = vr.company_id
        if cid not in entry_vr_map:
            entry_vr_map[cid] = vr
        exit_vr_map[cid] = vr   # keeps overwriting, ends on latest

    dist_map = {}
    for cf in all_cf:
        cid = cf.company_id
        dist_map[cid] = dist_map.get(cid, 0.0) + cf.amount_eur

    rows = []
    for inv in investments:
        cid       = inv.company_id
        entry_vr  = entry_vr_map.get(cid)
        exit_vr   = exit_vr_map.get(cid)
        is_exited = inv.exit_date is not None

        if entry_vr is None or exit_vr is None:
            continue

        ebitda_entry    = entry_vr.ebitda_ltm_eur
        ev_ebitda_entry = entry_vr.ev_ebitda
        net_debt_entry  = entry_vr.net_debt_eur
        entry_equity    = entry_vr.appraised_nav_eur

        if is_exited:
            ebitda_exit    = exit_vr.ebitda_ltm_eur
            ev_ebitda_exit = inv.exit_ev_ebitda or exit_vr.ev_ebitda
            net_debt_exit  = exit_vr.net_debt_eur
            exit_equity    = inv.exit_price_eur or exit_vr.appraised_nav_eur
        else:
            ebitda_exit    = exit_vr.ebitda_ltm_eur
            ev_ebitda_exit = exit_vr.ev_ebitda
            net_debt_exit  = exit_vr.net_debt_eur
            exit_equity    = exit_vr.appraised_nav_eur

        if any(v is None for v in [
            ebitda_entry, ev_ebitda_entry, net_debt_entry, entry_equity,
            ebitda_exit, ev_ebitda_exit, net_debt_exit, exit_equity,
        ]):
            continue

        distributions = dist_map.get(cid, 0.0)

        ebitda_growth      = (ebitda_exit - ebitda_entry) * ev_ebitda_entry
        multiple_expansion = (ev_ebitda_exit - ev_ebitda_entry) * ebitda_exit
        leverage_effect    = net_debt_entry - net_debt_exit
        total_attributed   = (
            ebitda_growth + multiple_expansion + leverage_effect + distributions
        )
        actual_value_created = exit_equity + distributions - entry_equity
        reconciliation_gap   = total_attributed - actual_value_created
        reconciliation_gap_pct = (
            reconciliation_gap / actual_value_created
            if actual_value_created != 0 else float('nan')
        )

        rows.append({
            'company_id':             cid,
            'company_name':           companies.get(cid, cid),
            'is_realised':            is_exited,
            'cost_basis':             inv.cost_basis_eur,
            'entry_equity_value':     entry_equity,
            'exit_equity_value':      exit_equity,
            'ebitda_growth':          ebitda_growth,
            'multiple_expansion':     multiple_expansion,
            'leverage_effect':        leverage_effect,
            'distributions':          distributions,
            'total_attributed':       total_attributed,
            'actual_value_created':   actual_value_created,
            'reconciliation_gap':     reconciliation_gap,
            'reconciliation_gap_pct': reconciliation_gap_pct,
            'gap_is_material':        abs(reconciliation_gap_pct) > GAP_THRESHOLD
                                        if not np.isnan(reconciliation_gap_pct) else False,
        })
       
    # Fund-level aggregation
    total_value_created = sum(r['actual_value_created'] for r in rows)
    total_cost          = sum(r['cost_basis'] for r in rows)

    component_cols = [
        'ebitda_growth', 'multiple_expansion', 'leverage_effect',
        'distributions', 'total_attributed', 'actual_value_created',
        'reconciliation_gap',
    ]
    fund_totals = {'total_cost_basis': total_cost}
    for col in component_cols:
        eur = sum(r[col] for r in rows)
        fund_totals[f'{col}_eur'] = eur
        fund_totals[f'{col}_pct'] = (
            eur / total_value_created if total_value_created != 0 else float('nan')
        )

    return {
        'fund_id':     fund_id,
        'company_id':  company_id,
        'rows':        rows,
        'fund_totals': fund_totals,
    }