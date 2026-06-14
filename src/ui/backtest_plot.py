"""
VaR backtest plotting utility.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.ui.plot_style import C, ACCENT, ACCENT2, section_title
from src.ui.nb_utils import save_fig


def plot_var_backtest(dates, returns, var_hist, fund_id, title=None, zone=None,
                      kupiec_pvalue=None, christoffersen_pvalue=None):
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
    kupiec_pvalue : float, optional
        Kupiec POF test p-value (0-1)
    christoffersen_pvalue : float, optional
        Christoffersen test p-value (0-1)

    Returns
    -------
    fig, ax
        Matplotlib figure and axes
    """
    # Convert to numpy arrays
    returns_arr = np.asarray(pd.to_numeric(returns, errors='coerce'))
    var_arr = np.asarray(pd.to_numeric(var_hist, errors='coerce'))
    x_axis = np.arange(len(returns_arr))

    # Increase figure size for legend outside and stats below
    fig, ax = plt.subplots(figsize=(10, 5.5))

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

    # Legend outside on right, top-aligned
    legend = ax.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1.02, 1))
    legend_bg = legend.get_frame()

    # Add test results below legend
    if kupiec_pvalue is not None or christoffersen_pvalue is not None:
        y_pos = 0.45

        # Kupiec test
        if kupiec_pvalue is not None:
            kupiec_result = 'PASS' if kupiec_pvalue > 0.05 else 'FAIL'
            kupiec_color = 'darkgreen' if kupiec_pvalue > 0.05 else 'darkred'

            ax.text(1.07, y_pos, 'Kupiec POF', transform=ax.transAxes,
                   fontsize=9, verticalalignment='top', family='monospace')
            ax.text(1.07, y_pos - 0.05, f'p={kupiec_pvalue:.4f}', transform=ax.transAxes,
                   fontsize=9, verticalalignment='top', family='monospace')
            ax.text(1.07, y_pos - 0.10, kupiec_result, transform=ax.transAxes,
                   fontsize=9, verticalalignment='top', family='monospace',
                   weight='bold', color=kupiec_color)

            y_pos -= 0.18

        # Christoffersen test
        if christoffersen_pvalue is not None:
            chris_result = 'PASS' if christoffersen_pvalue > 0.05 else 'FAIL'
            chris_color = 'darkgreen' if christoffersen_pvalue > 0.05 else 'darkred'

            ax.text(1.07, y_pos, 'Christoffersen', transform=ax.transAxes,
                   fontsize=9, verticalalignment='top', family='monospace')
            ax.text(1.07, y_pos - 0.05, f'p={christoffersen_pvalue:.4f}', transform=ax.transAxes,
                   fontsize=9, verticalalignment='top', family='monospace')
            ax.text(1.07, y_pos - 0.10, chris_result, transform=ax.transAxes,
                   fontsize=9, verticalalignment='top', family='monospace',
                   weight='bold', color=chris_color)

    plt.tight_layout()

    save_fig(fig, fund_id, "VaR backtest")
    plt.show()

    return fig, ax
