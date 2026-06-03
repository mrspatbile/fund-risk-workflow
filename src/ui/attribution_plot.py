"""
P&L attribution plotting utilities.
Visualizes daily factor decomposition (equity, rates, FX, residual).
"""

import matplotlib.pyplot as plt
from src.ui.plot_style import C, ACCENT, ACCENT2, ACCENT3, section_title
from src.ui.nb_utils import save_fig


def plot_attribution_cumsum(attr_cumsum, fund_id):
    """
    Plot cumulative P&L attribution by risk factor.

    Parameters
    ----------
    attr_cumsum : pd.DataFrame
        Cumulative attribution with columns:
        pnl_equity, pnl_rates, pnl_fx, pnl_residual (in EUR MM)
    fund_id : str
        Fund identifier for plot title

    Returns
    -------
    fig, ax
        Matplotlib figure and axes
    """

    fig, ax = plt.subplots(figsize=(11, 5))

    ax.plot(
        attr_cumsum.index,
        attr_cumsum['pnl_equity'],
        color=ACCENT,
        linewidth=1.5,
        label='Equity',
    )
    ax.plot(
        attr_cumsum.index,
        attr_cumsum['pnl_rates'],
        color=ACCENT2,
        linewidth=1.5,
        label='Rates',
    )
    ax.plot(
        attr_cumsum.index,
        attr_cumsum['pnl_fx'],
        color=ACCENT3,
        linewidth=1.5,
        label='FX',
    )
    ax.plot(
        attr_cumsum.index,
        attr_cumsum['pnl_residual'],
        color=C['red'],
        linewidth=1.0,
        linestyle='--',
        label='Residual',
    )

    ax.axhline(0, color='white', linewidth=0.5, linestyle='--')
    ax.set_ylabel('Cumulative P&L (EUR MM)')
    section_title(
        ax, f'Cumulative P&L Attribution by Risk Factor — {fund_id}', fontsize=18
    )
    ax.legend(fontsize=9)
    plt.tight_layout()

    save_fig(fig, fund_id, "05. PnL attribution")
    plt.show()

    return fig, ax
