"""
VaR backtest plotting utility.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.ui.plot_style import C, ACCENT, ACCENT2, section_title
from src.ui.nb_utils import save_fig


def plot_var_backtest(dates, returns, var_hist, fund_id, title=None, zone=None):
    """
    Plot VaR backtest — daily P&L vs VaR limit with breach highlighting.

    Parameters
    ----------
    dates : pd.Series or array-like
        Trading dates
    returns : pd.Series or array-like
        Daily P&L returns (decimal, e.g. 0.01 = 1%)
    var_hist : pd.Series or array-like
        VaR threshold (decimal, e.g. 0.02 = 2%)
    fund_id : str
        Fund identifier for filename
    title : str, optional
        Plot title. If None, uses 'VaR Backtest — {fund_id}'
    zone : str, optional
        ESMA zone ('Green', 'Amber', 'Red') to include in title

    Returns
    -------
    fig, ax
        Matplotlib figure and axes
    """
    # Convert to numpy arrays
    returns_arr = pd.to_numeric(returns, errors='coerce').values
    var_arr = pd.to_numeric(var_hist, errors='coerce').values
    x_axis = np.arange(len(returns_arr))

    # Plot
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(x_axis, returns_arr * 100,
            color=C['muted'], lw=0.9,
            label='Daily P&L', alpha=0.7)
    ax.plot(x_axis, -var_arr * 100,
            color=ACCENT, lw=1.2,
            label='99% VaR (historical)')

    # Highlight breaches
    breaches = returns_arr < -var_arr
    n_breaches = breaches.sum()
    ax.scatter(x_axis[breaches], returns_arr[breaches] * 100,
               color=ACCENT2, s=10, zorder=5,
               label=f'Breaches ({n_breaches})')

    # Title
    if title is None:
        title = f'VaR Backtest — {fund_id}'
    if zone:
        title += f' — Zone: {zone}'

    section_title(ax, title, fontsize=14)

    ax.set_ylabel('Daily P&L / VaR (%)', fontsize=9)
    ax.set_xlabel('Trading Days', fontsize=9)
    ax.legend(fontsize=10)
    plt.tight_layout()

    save_fig(fig, fund_id, "VaR backtest")
    plt.show()

    return fig, ax
