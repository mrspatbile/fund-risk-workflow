"""
VaR backtest plotting utility.
Single function handles both full history and ESMA 250-day reports.
"""

import pandas as pd
import matplotlib.pyplot as plt
from src.ui.plot_style import C, ACCENT, ACCENT2, section_title
from src.ui.nb_utils import save_fig


def plot_var_backtest(dates, returns, var_hist, fund_id, report_type='full', zone=None):
    """
    Plot VaR backtest — daily P&L vs VaR limit with breach highlighting.

    Parameters
    ----------
    dates : pd.Series or pd.Index
        Trading dates (aligned with returns and var_hist)
    returns : pd.Series or np.array
        Daily P&L returns (decimal, e.g. 0.01 = 1%)
    var_hist : pd.Series or np.array
        VaR threshold (decimal, e.g. 0.02 = 2%)
    fund_id : str
        Fund identifier for plot title (e.g. 'AIFM_HedgeFund')
    report_type : str
        'full' for full history, '250d' for ESMA 250-day exception report
    zone : str, optional
        ESMA exception zone ('Green', 'Amber', 'Red') for 250d reports

    Returns
    -------
    fig, ax
        Matplotlib figure and axes
    """

    # Extract 250-day window if requested
    if report_type == '250d':
        dates = dates.iloc[-250:].reset_index(drop=True)
        returns = returns[-250:]
        var_hist = var_hist.iloc[-250:].reset_index(drop=True)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(dates, returns * 100,
            color=C['muted'], lw=0.8 if report_type == 'full' else 1.2,
            label='Daily P&L', alpha=0.7)
    ax.plot(dates, -var_hist * 100,
            color=ACCENT, lw=1.2,
            label='99% VaR (historical)')

    # Highlight breaches
    breaches = returns < -var_hist.values
    n_breaches = breaches.sum()
    ax.scatter(dates[breaches], returns[breaches] * 100,
               color=ACCENT2, s=10, zorder=5,
               label=f'Breaches ({n_breaches})')

    # Title
    if report_type == 'full':
        title = f'VaR Backtest — {fund_id}'
        filename = "02. VAR backtest - full history"
    else:  # 250d
        zone_str = f' — Zone: {zone}' if zone else ''
        title = f'ESMA Exception Report — Last 250 Days{zone_str}'
        filename = "03. VAR backtest - last 250d"

    section_title(ax, title, fontsize=14 if report_type == '250d' else 15)

    ax.set_ylabel('Daily P&L / VaR (%)', fontsize=9)
    ax.legend(fontsize=10)
    plt.tight_layout()

    save_fig(fig, fund_id, filename)
    plt.show()

    return fig, ax
