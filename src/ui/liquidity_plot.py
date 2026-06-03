"""
Liquidity profile plotting utilities.
Visualizes liquidity bucket breakdown and concentration.
"""

import matplotlib.pyplot as plt
from src.ui.plot_style import C, ACCENT, section_title
from src.ui.nb_utils import save_fig


def plot_liquidity_profile(bucket_df, fund_id, metric='pct_nav_abs'):
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

    title = 'Liquidity Profile — Absolute Exposure by Bucket'
    section_title(ax, title, fontsize=10)

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

    plt.tight_layout()
    save_fig(fig, fund_id, "04. Liquidity buckets")
    plt.show()

    return fig, ax
