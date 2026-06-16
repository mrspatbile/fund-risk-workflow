"""Display helpers for liquidity calibration and LMT analysis.

Renders investor base summaries, redemption scenarios, and LMT trigger analysis.
"""

from IPython.display import display, HTML
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from src.ui.plot_style import C, ACCENT, ACCENT2, ACCENT3, apply_ax_style, section_title
from src.ui.print_html_utils import display_dark_table


def display_investor_base(
    investor_base: dict,
    fund_id: str,
    valuation_date: str,
    export_id: str | None = None,
):
    """Display investor base summary table.

    Parameters
    ----------
    investor_base : dict
        Investor register from investors.json with 'investors' list.

    fund_id : str
        Fund identifier.

    valuation_date : str
        Valuation date (e.g., '2026-05-13').

    export_id : str, optional
        If provided, save rendered output as PNG.
    """
    from src.computation.liquidity_calibration import summarize_investor_base_by_type

    summary_df = summarize_investor_base_by_type(investor_base)

    if summary_df.empty:
        display(HTML("<div style='color: #999; font-size: 12px;'>No investor data available.</div>"))
        return

    # Format display
    display_df = summary_df.copy()
    display_df['aum_pct'] = display_df['aum_pct'].apply(lambda x: f'{x*100:.1f}%')
    display_df['aum_eur'] = display_df['aum_eur'].apply(lambda x: f'€{x/1e6:.1f}m')

    html = display_dark_table(
        display_df,
        caption=f'Investor Base Summary — {fund_id}',
        col_align_override={'aum_pct': 'right', 'aum_eur': 'right'},
        col_widths={'investor_type': '180px', 'count': '60px', 'aum_pct': '100px', 'aum_eur': '120px'},
        return_html=True,
    )

    display(HTML(html))


def display_redemption_scenarios(
    scenarios_data: dict,
    fund_id: str,
    valuation_date: str,
    export_id: str | None = None,
):
    """Display calibrated redemption scenarios.

    Parameters
    ----------
    scenarios_data : dict
        Output from compute_redemption_scenarios() with keys:
        - 'redemption_scenarios': list of scenario dicts
        - 'largest_investor_name', 'largest_investor_pct'
        - 'weighted_normal_rate', 'weighted_stress_rate'

    fund_id : str
        Fund identifier.

    valuation_date : str
        Valuation date.

    export_id : str, optional
        If provided, save rendered output as PNG.
    """
    from src.computation.liquidity_calibration import format_scenario_for_display

    scenarios = scenarios_data.get('redemption_scenarios', [])
    largest_investor = scenarios_data.get('largest_investor_name', '—')
    largest_investor_pct = scenarios_data.get('largest_investor_pct', 0)

    rows = []
    for scenario in scenarios:
        name = scenario.get('name', '')
        pct = scenario.get('redemption_pct')

        if name == 'Largest investor':
            # Special formatting for largest investor
            if isinstance(pct, (int, float)):
                display_pct = f'{pct*100:.1f}% ({largest_investor})'
            else:
                display_pct = '—'
        else:
            if isinstance(pct, (int, float)):
                display_pct = f'{pct*100:.1f}%'
            else:
                display_pct = '—'

        rows.append({
            'Scenario': name,
            'Redemption': display_pct,
        })

    df = pd.DataFrame(rows)

    html = display_dark_table(
        df,
        caption=f'Redemption Scenarios — {fund_id}',
        col_align_override={'Redemption': 'right'},
        col_widths={'Scenario': '180px', 'Redemption': '200px'},
        return_html=True,
    )

    display(HTML(html))


def display_lmt_summary(
    df_result: pd.DataFrame,
    fund_id: str,
    valuation_date: str,
    export_id: str | None = None,
):
    """Display LMT trigger summary table.

    Parameters
    ----------
    df_result : pd.DataFrame
        Result from lmt_trigger_analysis() with columns:
        month, gate_active, swing_active, suspension_active, paid_eur, deferred_eur, backlog_eur, etc.

    fund_id : str
        Fund identifier.

    valuation_date : str
        Valuation date.

    export_id : str, optional
        If provided, save rendered output as PNG.
    """
    if df_result.empty:
        display(HTML("<div style='color: #999; font-size: 12px;'>No LMT analysis available.</div>"))
        return

    # Extract key metrics
    gate_months = df_result[df_result['gate_active']]['month'].tolist()
    swing_months = df_result[df_result['swing_active']]['month'].tolist()
    suspension_months = df_result[df_result['suspension_active']]['month'].tolist()

    summary_rows = [
        ('Gate first fires (month)', gate_months[0] if gate_months else '—'),
        ('Swing first fires (month)', swing_months[0] if swing_months else '—'),
        ('Suspension triggers (month)', suspension_months[0] if suspension_months else '—'),
        ('Peak backlog (€m)', f"{df_result['backlog_eur'].max() / 1e6:.1f}"),
        ('Total paid over period (€m)', f"{df_result['paid_eur'].sum() / 1e6:.1f}"),
        ('Terminal liquid NAV (€m)', f"{df_result['liquid_nav_eur'].iloc[-1] / 1e6:.1f}"),
    ]

    df_display = pd.DataFrame(summary_rows, columns=['Metric', 'Value'])

    html = display_dark_table(
        df_display,
        caption=f'LMT Trigger Summary — {fund_id}',
        col_align_override={'Value': 'right'},
        col_widths={'Metric': '240px', 'Value': '150px'},
        return_html=True,
    )

    display(HTML(html))


def plot_lmt_analysis(
    df_result: pd.DataFrame,
    fund_id: str,
    valuation_date: str,
    export_id: str | None = None,
):
    """Plot LMT analysis: paid/deferred/backlog, NAV evolution, LMT flags.

    Parameters
    ----------
    df_result : pd.DataFrame
        Result from lmt_trigger_analysis().

    fund_id : str
        Fund identifier.

    valuation_date : str
        Valuation date.

    export_id : str, optional
        If provided, save rendered output as PNG.
    """
    months = df_result['month'].values

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # Panel 1: Paid / Deferred / Backlog
    ax = axes[0]
    ax.bar(months, df_result['paid_eur'] / 1e6, color=ACCENT, label='Paid', width=0.5)
    ax.bar(
        months,
        df_result['deferred_eur'] / 1e6,
        color=ACCENT2,
        label='Deferred',
        bottom=df_result['paid_eur'] / 1e6,
        width=0.5,
    )
    ax2 = ax.twinx()
    ax2.plot(
        months,
        df_result['backlog_eur'] / 1e6,
        color=ACCENT3,
        marker='o',
        linewidth=1.5,
        label='Backlog (rhs)',
    )
    ax2.set_ylabel('Backlog (EUR m)', fontsize=8)
    ax.set_xlabel('Month')
    ax.set_ylabel('EUR m')
    ax.set_title('Paid / Deferred / Backlog')
    ax.legend(loc='upper left', fontsize=7)
    ax2.legend(loc='upper right', fontsize=7)

    # Panel 2: NAV Evolution
    ax = axes[1]
    ax.stackplot(
        months,
        df_result['liquid_nav_eur'] / 1e6,
        df_result['illiquid_nav_eur'] / 1e6,
        labels=['Liquid NAV', 'Illiquid NAV'],
        colors=[ACCENT, ACCENT2],
        alpha=0.8,
    )
    ax.set_xlabel('Month')
    ax.set_ylabel('EUR m')
    ax.set_title('NAV Evolution')
    ax.legend(loc='upper right', fontsize=7)

    # Panel 3: LMT Flags
    ax = axes[2]
    for i, (col, color, lbl) in enumerate([
        ('gate_active', ACCENT, 'Gate'),
        ('swing_active', ACCENT2, 'Swing'),
        ('suspension_active', ACCENT3, 'Suspension'),
    ]):
        ax.step(months, df_result[col].astype(int) + i * 1.2, where='post', color=color, linewidth=2, label=lbl)
    ax.set_yticks([0, 1.2, 2.4])
    ax.set_yticklabels(['Gate', 'Swing', 'Suspension'], fontsize=8)
    ax.set_xlabel('Month')
    ax.set_title('LMT Flags Active')
    ax.set_ylim(-0.3, 3.5)

    fig.suptitle(f'LMT Trigger Analysis — {fund_id}', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.show()


def suggest_liquidity_policy_block(
    fund_id: str,
    scenarios_data: dict,
    nav_eur: float,
    notice_period_days: int,
    stress_window_days: int,
) -> dict:
    """Generate a suggested liquidity_monitoring block for risk_policy.json.

    This is for informational output only. The block can be reviewed and
    manually added to risk_policy.json if appropriate.

    Parameters
    ----------
    fund_id : str
        Fund identifier.

    scenarios_data : dict
        Output from compute_redemption_scenarios().

    nav_eur : float
        Fund NAV in EUR.

    notice_period_days : int
        Contractual notice period (e.g., 1 for UCITS, 30 for HF).

    stress_window_days : int
        Liquidity stress window (e.g., 5 for UCITS, 30 for HF).

    Returns
    -------
    dict
        Suggested liquidity_monitoring block ready for JSON serialization.
    """
    scenarios = scenarios_data.get('redemption_scenarios', [])

    policy_block = {
        'pct_adv': 0.25,
        'stress_window_days': stress_window_days,
        'notice_period_days': notice_period_days,
        'redemption_scenarios': scenarios,
        '_note': f'Calibrated {len(scenarios)} redemption scenarios from investor base on {fund_id}. '
                 'Scenarios reflect historical investor behaviour and stress assumptions. '
                 'Update if investor mix or market conditions change materially.',
    }

    return policy_block


def display_suggested_policy_block(
    policy_block: dict,
    fund_id: str,
):
    """Display suggested liquidity_monitoring block as formatted JSON.

    Parameters
    ----------
    policy_block : dict
        Suggested policy block from suggest_liquidity_policy_block().

    fund_id : str
        Fund identifier.
    """
    import json

    json_str = json.dumps(policy_block, indent=2)
    html = f"""
    <div style="background-color: #1e1e1e; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 11px; overflow-x: auto; color: #d4d4d4;">
        <div style="color: #ce9178; margin-bottom: 8px;"><strong>Suggested liquidity_monitoring block for {fund_id}/risk_policy.json:</strong></div>
        <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">{json_str}</pre>
    </div>
    """
    display(HTML(html))


def plot_liquidity_profile_chart(
    funds_data: dict,
    valuation_date: str,
    bucket_order: list | None = None,
    export_id: str | None = None,
):
    """Plot liquidity bucket distribution for multiple funds.

    Parameters
    ----------
    funds_data : dict
        Dict mapping fund_id to DataFrames with liquidity buckets.
        E.g., {'UCITS_Balanced': df_with_liquidity_bucket_col}

    valuation_date : str
        Valuation date for display.

    bucket_order : list, optional
        Order of liquidity buckets. Default: ['1 day', '2-7 days', '8-30 days', '31-90 days', '91-365 days', '> 1 year']

    export_id : str, optional
        If provided, save figure to figs/.
    """
    from src.ui.nb_utils import save_fig

    if bucket_order is None:
        bucket_order = ['1 day', '2-7 days', '8-30 days', '31-90 days', '91-365 days', '> 1 year']

    fig, axes = plt.subplots(1, len(funds_data), figsize=(6 * len(funds_data), 5))
    if len(funds_data) == 1:
        axes = [axes]

    for ax, (fund_id, df) in zip(axes, funds_data.items()):
        nav = df['market_value_eur'].sum()
        bkt = (df.groupby('liquidity_bucket', observed=True)['market_value_eur']
                  .sum().reindex(bucket_order, fill_value=0.0))
        pcts = (bkt / nav * 100).values

        bars = ax.bar(range(len(bucket_order)), pcts, color=C['cyan'], width=0.6)
        ax.set_xticks(range(len(bucket_order)))
        ax.set_xticklabels(['1d', '2-7d', '8-30d', '31-90d', '91-365d', '>1yr'], fontsize=8)
        ax.set_ylabel('% of NAV', fontsize=8)
        section_title(ax, fund_id)
        ax.set_ylim(0, 115)
        for bar, pct in zip(bars, pcts):
            if pct > 2:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f'{pct:.0f}%', ha='center', va='bottom', fontsize=7)

    fig.suptitle('ESMA Liquidity Bucket Distribution', fontsize=12, fontweight='bold')
    plt.tight_layout()

    if export_id:
        save_fig(fig, '', export_id)

    plt.show()


def display_redemption_stress_table(
    stress_results: dict,
    valuation_date: str,
    export_id: str | None = None,
):
    """Display single-period redemption stress table.

    Parameters
    ----------
    stress_results : dict
        Dict with fund results, each containing NAV, redemption amount, liquid assets, etc.

    valuation_date : str
        Valuation date.

    export_id : str, optional
        If provided, save rendered output as PNG.
    """
    stress_rows = []
    for fund_name, result in stress_results.items():
        stress_rows.append({
            'Fund': fund_name,
            'NAV (€m)': f"{result['nav'] / 1e6:.1f}",
            'Redemption (€m)': f"{result['redemption_amount_eur'] / 1e6:.1f}",
            'Liquid Assets (€m)': f"{result['liquid_assets_eur'] / 1e6:.1f}",
            'Coverage Ratio': f"{result['coverage_ratio']:.2f}x",
            'Can Meet': '✓' if result.get('can_meet_redemption', True) else '✗',
        })

    df = pd.DataFrame(stress_rows).set_index('Fund')

    html = display_dark_table(
        df,
        caption='Redemption Stress — Single-Period Snapshot (25% NAV, 5-day notice)',
        col_align_override={'Coverage Ratio': 'right'},
        col_widths={'Fund': '150px', 'NAV (€m)': '120px', 'Coverage Ratio': '120px'},
        return_html=True,
    )

    display(HTML(html))


def display_lmt_cross_fund_summary(
    lmt_results: dict,
    valuation_date: str,
    export_id: str | None = None,
):
    """Display cross-fund LMT trigger summary.

    Parameters
    ----------
    lmt_results : dict
        Dict mapping fund_name to LMT result DataFrames.

    valuation_date : str
        Valuation date.

    export_id : str, optional
        If provided, save rendered output as PNG.
    """
    summary_rows = []
    for fname, df in lmt_results.items():
        gate_m = df[df['gate_active']]['month'].tolist()
        swing_m = df[df['swing_active']]['month'].tolist()
        susp_m = df[df['suspension_active']]['month'].tolist()
        summary_rows.append({
            'Fund': fname,
            'Gate first (month)': gate_m[0] if gate_m else '—',
            'Swing first (month)': swing_m[0] if swing_m else '—',
            'Suspension (month)': susp_m[0] if susp_m else '—',
            'Peak backlog (€m)': f"{df['backlog_eur'].max() / 1e6:.1f}",
            'Total paid (€m)': f"{df['paid_eur'].sum() / 1e6:.1f}",
        })

    df_summary = pd.DataFrame(summary_rows).set_index('Fund')

    html = display_dark_table(
        df_summary,
        caption='LMT Trigger Summary — Cross-Fund Analysis',
        col_align_override={col: 'right' for col in df_summary.columns},
        return_html=True,
    )

    display(HTML(html))
