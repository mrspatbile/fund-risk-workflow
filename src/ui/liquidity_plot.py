"""
Liquidity profile plotting utilities.
Visualizes liquidity bucket breakdown and concentration.
"""

import matplotlib.pyplot as plt
from src.ui.plot_style import C, ACCENT, FONT
from src.ui.nb_utils import save_fig


def plot_liquidity_profile(bucket_df, fund_id, metric='pct_nav_abs', valuation_date: str | None = None):
    """
    Plot liquidity profile — exposure by bucket with value labels.

    Parameters
    ----------
    bucket_df : pd.DataFrame
        Liquidity bucket breakdown with columns:
        - liquidity_bucket : str
        - pct_nav_abs : float (absolute exposure % NAV)
        - pct_nav_signed : float (signed exposure % NAV)
    fund_id : str
        Fund identifier for file naming
    metric : str, optional
        Column to plot ('pct_nav_abs' or 'pct_nav_signed'). Default 'pct_nav_abs'
    valuation_date : str, optional
        Valuation date for subtitle

    Returns
    -------
    fig, ax
        Matplotlib figure and axes
    """

    fig, ax = plt.subplots(figsize=(7, 3))

    bars = ax.bar(
        bucket_df['liquidity_bucket'],
        bucket_df[metric],
        color=ACCENT,
        alpha=0.85,
        width=0.5,
    )

    ax.axhline(0, color=C['dim'], lw=0.8)
    ax.set_ylabel('Absolute Exposure (% NAV)', fontsize=9)

    # Main title as figure suptitle
    fig.suptitle(
        'Liquidity Profile — Absolute Exposure by Bucket',
        fontsize=11,
        fontweight='bold',
        color=C['cyan'],
        ha='left',
        x=0.03,
    )

    # Valuation date as axes title (below suptitle)
    if valuation_date:
        ax.set_title(
            f'As of {valuation_date}',
            fontsize=9.5,
            fontweight='normal',
            color=C['muted'],
            loc='left',
            pad=0,
        )

    # Label bars with values > 2%
    for bar, val in zip(bars, bucket_df[metric]):
        if val > 2:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val / 2,
                f'{val:.1f}%',
                ha='center',
                va='center',
                fontsize=8,
                color='white',
                fontweight='bold',
            )

    plt.tight_layout(rect=[0, 0, 1, 1.05])
    save_fig(fig, fund_id, "04. Liquidity buckets")
    plt.show()

    return fig, ax
