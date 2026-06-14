from IPython.display import display, HTML
import re
import pandas as pd
from datetime import datetime, timedelta
from src.ui.plot_style import C
from src.risk.risk_utils import redemption_stress
from src.config import VALUATION_DATE


def _xnav(prefix: str = '') -> str:
    """Column name that display_dark_table renders as PREFIX\n(×NAV).
    Use wherever a column represents an exposure as a multiple of NAV.
    The × (U+00D7) is unaffected by CSS text-transform: uppercase.
    """
    return f'{prefix}\n(×NAV)' if prefix else '\n(×NAV)'


def display_dark_table(
    df,
    caption                   : str        = '',
    fmt                       : dict | None = None,
    col_styles                : dict | None = None,
    col_align_override        : dict | None = None,
    highlight_rows            : list | None = None,
    col_header_align_override : dict | None = None,
    col_widths : dict | None = None,  # e.g. {'metric': '200px', 'value': '100px'}
    spacer_width              : str | None = None,  # e.g. '100px' — adds invisible spacer column
    date_str                  : str | None = None,  # e.g. '2026-05-13' — shown below caption
    date_label                : str        = 'As of',  # label for the date line
    hide_header               : bool       = False,  # hide column headers by matching text to background
    return_html               : bool       = False,  # if True, return HTML string instead of displaying
):
    """
    Render a DataFrame as a dark-themed styled HTML table in Jupyter.

    Consistent with the board report visual identity. Column names are
    auto-formatted: underscores replaced by spaces, EUR columns get a
    second line '(EUR)', all names title-cased.

    Parameters
    ----------
    df : pd.DataFrame
        Data to display. Original column names are used for fmt and
        col_styles keys — renaming happens internally for display only.

    caption : str
        Table title. Rendered in cyan, left-aligned, above the table.

    fmt : dict, optional
        Format strings keyed by original column name.
        e.g. {'market_value_eur': '{:,.0f}', 'weight_pct': '{:.2f}%'}
        Missing values rendered as '—'.

    col_styles : dict, optional
        Per-column color functions keyed by original column name.
        Each value is a callable: (cell_value) -> color_str or None.
        None means no color override (keeps default muted grey).
        e.g. {'esg_score': lambda v: C['green'] if v >= 70 else C['red']}

    col_align_override : dict, optional
        Override auto-detected alignment for specific columns (both
        header and cells). Keyed by original column name.
        Auto-detection: numeric/bool -> right, text -> center, first col -> left.
        e.g. {'esg_score': 'center'}

    highlight_rows : list, optional
        List of integer index values to render as section headers —
        uppercase, distinct background, letter-spacing.
        e.g. [0, 5] highlights the first and sixth rows.

    col_header_align_override : dict, optional
        Override alignment for column headers only, independently of
        cell alignment. Keyed by original column name.
        e.g. {'market_value_eur': 'center'} keeps cells right-aligned
        but centres the header.

    spacer_width : str, optional
        Width of invisible spacer column (last column). Useful for normalizing
        table widths across multiple tables with different content.
        e.g. '100px' adds an invisible 100px column at the end.
        Column is hidden (visibility: hidden) but takes up space.

    Notes
    -----
    - Index is always hidden.
    - Requires C (colour palette dict) from plot_style to be in scope.
    - ESG example: use ESG_COL_STYLES and ESG_FMT as col_styles and fmt.
    """
    
    _UPPER = {'Eur', 'Nav', 'Aum', 'Otc', 'Lcr', 'Rag', 'Dpi', 'Irr', 'Esg',
              'Env', 'Soc', 'Gov', 'Pai', 'Hhi', 'Pb', 'Id', 'Qtd'}

    def _fmt_col(col):
        # Spacer column header should be empty
        if col == '__spacer__':
            return ''
        col = col.replace('_', ' ').replace('pct', '%')
        # Normalize all NAV % variants to % NAV
        col = col.replace('NAV %', '% NAV')
        col = col.replace('nav %', '% NAV')
        # Standalone 'n' (count columns: n_obs, n_positions …) → qtd
        col = re.sub(r'\bn\b', 'qtd', col)
        if 'eur' in col.lower() and '(eur)' not in col.lower():
            # case-insensitive strip; if nothing is left (col was just 'EUR')
            # keep it as-is — no parentheses, no repetition
            col_stripped = col.lower().replace('eur', '').strip()
            if col_stripped:
                col = f'{col_stripped}\n(EUR)'
        titled = col.title()
        for abbrev in _UPPER:
            titled = titled.replace(abbrev, abbrev.upper())
        return titled

    df = df.replace(0, float('nan'))
    df_display          = df.rename(columns={c: _fmt_col(c) for c in df.columns})
    col_map             = dict(zip(df.columns, df_display.columns))

    # Add invisible spacer column if requested
    # spacer_width controls the visual width via repeated characters (e.g. '_' * 80)
    if spacer_width:
        spacer_col = '__spacer__'
        # Parse spacer_width as number of characters (e.g. '80' → 80 chars)
        try:
            n_chars = int(spacer_width.replace('px', '').strip())
            df_display[spacer_col] = '_' * n_chars
        except:
            df_display[spacer_col] = ''
    col_styles_remapped = {col_map[k]: v for k, v in col_styles.items() if k in col_map} if col_styles else None
    fmt_remapped        = {col_map.get(k, k): v for k, v in fmt.items()} if fmt else None

    def _style(df):
        styles = []
        for row_num, (i, row) in enumerate(df.iterrows()):
            is_highlight   = highlight_rows and i in highlight_rows
            bg             = "#36394F" if is_highlight else ('#1a1f2e' if row_num % 2 == 0 else '#141929')
            color          = '#587580' if is_highlight else C['muted']
            fw             = 'bold'   if is_highlight else 'normal'
            text_transform = 'uppercase' if is_highlight else 'none'
            letter_spacing = '0.05em'   if is_highlight else 'normal'
            font_size      = '10px'     if is_highlight else '11px'
            base = (f'background-color: {bg}; color: {color}; font-weight: {fw}; '
                    f'font-family: Arial, sans-serif; font-size: {font_size}; '
                    f'text-transform: {text_transform}; letter-spacing: {letter_spacing};')
            row_style = [base] * len(df.columns)
            if col_styles_remapped:
                for col, color_fn in col_styles_remapped.items():
                    if col in df.columns:
                        idx   = df.columns.get_loc(col)
                        color = color_fn(row[col])
                        if color:
                            row_style[idx] = (f'background-color: {bg}; color: {color}; '
                                              f'font-weight: bold; font-family: Arial, sans-serif; font-size: 11px;')
            styles.append(row_style)
        return pd.DataFrame(styles, index=df.index, columns=df.columns)

    def _col_align(df):
        aligns = {}
        for col in df.columns:
            try:
                if df[col].dtype in ('float64', 'int64', 'bool'):
                    aligns[col] = 'right'
                else:
                    aligns[col] = 'center'
            except Exception:
                aligns[col] = 'center'
        aligns[df.columns[0]] = 'left'
        return aligns

    # Build header styles — optionally hidden
    thead_props = [
        ('background-color', '#2F3245'),
        ('font-family',      'Arial, sans-serif'),
        ('font-size',        '1px' if hide_header else '10px'),
        ('font-weight',      'bold'),
        ('padding',          '0px' if hide_header else '6px 12px'),
        ('border-bottom',    '2px solid #0f1729'),
        ('color',            '#2F3245' if hide_header else '#a5cfdf'),  # match background if hidden
        ('letter-spacing',   '0.05em'),
        ('text-transform',   'uppercase'),
        ('white-space',      'pre-wrap'),
        ('line-height',      '1px' if hide_header else 'normal'),
    ]

    table_styles = [
        {'selector': 'caption', 'props': [
            ('color',            C['cyan']),
            ('font-size',        '14px'),
            ('font-weight',      'bold'),
            ('text-align',       'left'),
            ('font-family',      'Helvetica Neue, Helvetica, Arial, sans-serif'),
            ('padding-bottom',   '8px'),
            ('padding-left',     '10px'),
            ('background-color', '#1a2540'),
        ]},
        {'selector': 'thead th', 'props': thead_props},
        {'selector': 'td', 'props': [
            ('padding',       '5px 12px'),
            ('border-bottom', '1px solid #0f1729'),
            ('font-family',   'Arial, sans-serif'),
        ]},
        {'selector': 'table', 'props': [
            ('border-collapse', 'collapse'),
            ('width',           '100%'),
        ]},
    ]

    # Hide spacer column text but keep width (text color = background, so invisible)
    if spacer_width and '__spacer__' in df_display.columns:
        spacer_col_idx = df_display.columns.get_loc('__spacer__') + 1
        table_styles.append({
            'selector': f'thead th:nth-child({spacer_col_idx})',
            'props'   : [('color', '#2F3245')]  # Header bg color — text invisible
        })
        table_styles.append({
            'selector': f'td:nth-child({spacer_col_idx})',
            'props'   : [('color', '#1a1f2e')]  # Row bg color — text invisible, keeps width
        })

    aligns = _col_align(df_display)
    if col_align_override:
        for col, align in col_align_override.items():
            remapped = col_map.get(col, col)
            if remapped in aligns:
                aligns[remapped] = align

    for col, align in aligns.items():
        col_idx = df_display.columns.get_loc(col) + 1
        table_styles.append({
            'selector': f'td:nth-child({col_idx})',
            'props'   : [('text-align', f'{align} !important')]
        })
        table_styles.append({
            'selector': f'thead th:nth-child({col_idx})',
            'props'   : [('text-align', f'{align} !important')]
        })
    if col_widths:
        for col, width in col_widths.items():
            remapped = col_map.get(col, col)
            if remapped in df_display.columns:
                col_idx = df_display.columns.get_loc(remapped) + 1
                table_styles.append({
                    'selector': f'thead th:nth-child({col_idx})',
                    'props'   : [('width', width), ('min-width', width)]
                })

    # override header alignment only
    if col_header_align_override:
        for col, align in col_header_align_override.items():
            remapped = col_map.get(col, col)
            if remapped in df_display.columns:
                col_idx = df_display.columns.get_loc(remapped) + 1
                table_styles.append({
                    'selector': f'thead th:nth-child({col_idx})',
                    'props'   : [('text-align', f'{align} !important')]
                })

    styled = df_display.style.apply(_style, axis=None).set_table_styles(table_styles)

    if caption:
        if date_str:
            caption = f'{caption}<br><span style="font-size: 10px; font-weight: normal; color: #999; margin-top: 4px; display: block;">{date_label} {date_str}</span>'
        styled = styled.set_caption(caption)
    if fmt_remapped:
        styled = styled.format(fmt_remapped, na_rep='—')

    styled = styled.hide(axis='index')

    if return_html:
        return styled.to_html()
    else:
        display(styled)

#-------------------
# general info displays
#-------------------

def display_fund_rmp_parameters(fund_id: str, engine, export_id: str | None = None):
    """
    Display fund's Risk Management Policy parameters grouped by section.

    Reads fund's risk_policy.json and displays all parameters grouped by
    top-level sections (var_framework, leverage_limits, etc.).
    Adapts to any fund type (AIFM, UCITS, PE, private debt, real estate, etc).
    Internal notes (_note_*) shown at bottom.

    Parameters
    ----------
    fund_id : str
        Fund identifier
    engine : sqlalchemy.engine
        Database engine (passed for consistency with other display functions)
    export_id : str or None, default None
        If provided, save rendered HTML as PNG to reports/<fund_id>/<export_id>_*.png
    """
    import json
    from pathlib import Path

    # Relative path from this module (src/ui/) to reference_data/
    module_dir = Path(__file__).parent
    risk_policy_path = module_dir / '../../reference_data' / 'funds' / fund_id / 'risk_policy.json'
    with open(risk_policy_path) as f:
        rmp = json.load(f)

    rows = []
    notes = []

    # Section title mappings (maps actual JSON keys to display titles)
    section_titles = {
        'var_framework': 'VaR Framework',
        'expected_shortfall': 'Expected Shortfall',
        'backtesting': 'VaR Backtesting',
        'var_backtesting': 'VaR Backtesting',
        'leverage_limits': 'Leverage Limits',
        'leverage_limits_internal': 'Leverage Limits',
        'concentration_limits': 'Concentration Limits',
        'concentration_limits_internal': 'Concentration Limits',
        'stress_testing': 'Stress Testing',
        'stress_scenarios': 'Stress Testing',
        'investor_concentration': 'Investor Concentration Monitoring',
        'investor_concentration_monitoring': 'Investor Concentration Monitoring',
        'liquidity_monitoring': 'Liquidity Monitoring',
        'redemption_terms': 'Redemption Terms',
    }

    # Top-level field mappings (non-nested fields)
    top_level_fields = {
        'fund_id': 'Fund ID',
        'liquidity_profile': 'Liquidity Profile',
        'valuation_frequency': 'Valuation Frequency',
        'notice_period_days': 'Notice Period',
        'lockup_days': 'Lockup Period',
    }

    # Field name to readable label conversions
    field_labels = {
        'confidence_level': 'Confidence level',
        'holding_period_days': 'Holding period',
        'lookback_period_days': 'Lookback period',
        'models': 'Models',
        'distribution': 'Distribution',
        'observation_window': 'Observation window',
        'tests': 'Tests',
        'acceptable_breach_rate': 'Acceptable breach rate',
        'monitoring_threshold': 'Monitoring threshold',
        'gross_leverage': 'Gross leverage',
        'commitment_leverage': 'Commitment leverage',
        'notional_leverage': 'Notional leverage',
        'single_issuer': 'Single issuer',
        'single_sector': 'Single sector',
        'single_country': 'Single country',
        'enabled': 'Enabled',
        'scenario_types': 'Scenario types',
        'single_investor_threshold': 'Single investor threshold',
        'top_3_investors_threshold': 'Top 3 investors threshold',
        'top_5_investors_threshold': 'Top 5 investors threshold',
        'structure': 'Structure',
        'redemption_frequency': 'Redemption frequency',
        'redemption_notice_days': 'Redemption notice',
        'redemption_settlement_days': 'Settlement',
        'display': 'Display',
        'liquidity_profile': 'Liquidity profile',
        'valuation_frequency': 'Valuation frequency',
        'breach_rate_thresholds': 'Breach rate thresholds',
        'acceptable_pct': 'Acceptable',
        'monitor_pct': 'Monitor',
        'parametric_distribution': 'Distribution',
        'parametric_degrees_of_freedom': 'Degrees of freedom',
        'scaling_method': 'Scaling method',
        'use_var': 'Use VaR',
        'use_backtesting': 'Use backtesting',
        'use_stress_testing': 'Use stress testing',
        'gross_leverage_max': 'Gross leverage',
        'commitment_leverage_max': 'Commitment leverage',
        'single_issuer_max_pct': 'Single issuer',
        'single_investor_threshold_pct': 'Single investor threshold',
        'top_3_investors_threshold_pct': 'Top 3 investors threshold',
        'top_5_investors_threshold_pct': 'Top 5 investors threshold',
        'scenario_types': 'Scenario types',
    }

    def format_value(value, field_name=''):
        """Format a value for display."""
        if value is None or value == '' or (isinstance(value, list) and len(value) == 0):
            return None

        if isinstance(value, bool):
            return 'Yes' if value else 'No'
        elif isinstance(value, list):
            return ', '.join(str(v) for v in value)
        elif isinstance(value, (int, float)):
            # Format as percentage if field name contains 'pct'
            if 'pct' in field_name.lower():
                return f'{value:.1f}%'
            # Format as leverage multiplier if field name contains 'leverage'
            if 'leverage' in field_name.lower():
                return f'{value:.2f}x'
            # Format large numbers with thousands separators
            if abs(value) >= 1_000_000:
                return f"{int(value):,}"
            return str(value)
        else:
            return str(value)

    def readable_label(field_name):
        """Convert field name to readable label."""
        return field_labels.get(field_name, field_name.replace('_', ' ').title())

    # First, process top-level fields
    top_level_section_added = False
    for field_key, field_title in top_level_fields.items():
        if field_key in rmp:
            field_value = rmp[field_key]
            formatted = format_value(field_value, field_key)
            if formatted is not None:
                if not top_level_section_added:
                    rows.append(('Fund Parameters', ''))
                    top_level_section_added = True
                label = field_title
                rows.append((f'  {label}', formatted))

    if top_level_section_added:
        rows.append(('', ''))  # Spacer

    # Process each top-level section (nested objects)
    for section_key, section_title in section_titles.items():
        if section_key not in rmp:
            continue

        section_data = rmp[section_key]
        if not section_data or (isinstance(section_data, dict) and all(
            k.startswith('_') or v is None or v == '' or (isinstance(v, list) and len(v) == 0)
            for k, v in section_data.items()
        )):
            continue

        # Add section header
        rows.append((section_title, ''))

        # Add parameters under section
        if isinstance(section_data, dict):
            for param_key, param_value in section_data.items():
                # Skip notes and empty values
                if param_key.startswith('_'):
                    notes.append((param_key.lstrip('_'), param_value if isinstance(param_value, str) else str(param_value)))
                    continue

                # Handle nested dicts by flattening into comma-separated string
                if isinstance(param_value, dict):
                    label = readable_label(param_key)
                    sub_items = []
                    for sub_key, sub_value in param_value.items():
                        if not sub_key.startswith('_'):
                            formatted = format_value(sub_value, sub_key)
                            if formatted is not None:
                                sub_label = readable_label(sub_key)
                                sub_items.append(f'{sub_label}: {formatted}')
                    if sub_items:
                        rows.append((f'  {label}', ', '.join(sub_items)))
                else:
                    formatted = format_value(param_value, param_key)
                    if formatted is not None:
                        # Indent parameter name
                        label = readable_label(param_key)
                        rows.append((f'  {label}', formatted))

        # Add spacer after section
        rows.append(('', ''))

    # Add notes at bottom with text wrapping
    if notes:
        for note_key, note_value in notes:
            # Wrap long notes at word boundaries (max 100 chars per line)
            if len(note_value) > 100:
                wrapped_lines = []
                words = note_value.split()
                current_line = []
                current_length = 0

                for word in words:
                    if current_length + len(word) + 1 <= 100:  # +1 for space
                        current_line.append(word)
                        current_length += len(word) + 1
                    else:
                        if current_line:
                            wrapped_lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = len(word) + 1

                if current_line:
                    wrapped_lines.append(' '.join(current_line))

                note_value = '\n'.join(wrapped_lines)

            rows.append((f"Note: {note_key}", note_value))

    if rows:
        # Remove trailing empty rows
        while rows and rows[-1] == ('', ''):
            rows.pop()

        # Find section header rows (no indentation, no notes)
        highlight_indices = []
        for idx, (param, value) in enumerate(rows):
            if param and not param.startswith('  ') and not param.startswith('Note:') and value == '':
                highlight_indices.append(idx)

        df = pd.DataFrame(rows, columns=['Parameter', 'Value'])

        html = display_dark_table(
            df,
            caption='Risk Management Policy Parameters',
            col_align_override={'Value': 'left'},
            col_widths={'Parameter': '250px', 'Value': '320px'},
            highlight_rows=highlight_indices,
            col_styles={
                'Parameter': lambda v: (
                    C['muted'] if isinstance(v, str) and v and not v.startswith('  ') and not v.startswith('Note:')
                    else None
                ),
            },
            hide_header=True,
            return_html=True,
        )

        display(HTML(html))

        if export_id is not None:
            from src.ui.nb_utils import _slugify, save_html_as_png
            title_slug = _slugify('Risk Management Policy Parameters')
            filename = f'{export_id}_{title_slug}'
            save_html_as_png(html, fund_id, filename)
    else:
        display(HTML("<div style='color: #999; font-size: 12px;'>No RMP parameters defined.</div>"))


def display_fund_overview_banner(fund_id: str, engine, export_id: str | None = None):
    """
    Display fund overview: which fund is being studied.

    Queries fund_profile.json to show fund identity and classification.
    No snapshot-specific data (NAV, valuation date, etc).

    Optionally saves rendered output as PNG with deterministic filename when export_id is provided.

    Parameters
    ----------
    fund_id : str
        Fund identifier
    engine : sqlalchemy.engine
        Database engine (passed for consistency with other display functions)
    export_id : str or None, default None
        If provided, save rendered HTML as PNG to reports/<fund_id>/<export_id>_fund_overview.png
        If None, display normally without saving.

    Returns
    -------
    None
    """
    import json
    from pathlib import Path
    from src.ui.nb_utils import _slugify, save_html_as_png

    # Relative path from this module (src/ui/) to reference_data/
    module_dir = Path(__file__).parent
    fund_profile_path = module_dir / '../../reference_data' / 'funds' / fund_id / 'fund_profile.json'
    with open(fund_profile_path, 'r') as f:
        profile = json.load(f)

    # Regulatory classification
    reg = profile['regulatory_classification']
    if reg['is_ucits']:
        fund_class = 'UCITS'
    elif reg['is_aif']:
        fund_class = 'AIF (AIFM)'
    else:
        fund_class = profile['fund_type']

    # Build banner rows - fund identity only
    long_name = profile.get('fund_name', fund_id)

    # Redemption terms
    redemption_terms = profile.get('redemption_terms', {})
    redemption_display = redemption_terms.get('display', '—')

    rows = [
        ('Fund Name', long_name),
        ('Fund Code', fund_id),
        ('Fund Type', fund_class),
        ('Domicile', profile['domicile']),
        ('Currency', profile['currency']),
    ]

    # Add redemption terms if available
    if redemption_display != '—':
        rows.append(('Redemption terms', redemption_display))

    df = pd.DataFrame(rows, columns=['label', 'value'])

    # Get HTML and display it
    html = display_dark_table(
        df,
        caption='Fund',
        col_align_override={'value': 'left'},
        col_widths={'label': '160px', 'value': '300px'},
        return_html=True,
    )

    # Display in notebook
    display(HTML(html))

    # Save as PNG if export_id is provided
    if export_id is not None:
        title_slug = _slugify('Fund')
        filename = f'{export_id}_{title_slug}'
        save_html_as_png(html, fund_id, filename)


def display_fund_summary(FUND_ID, VALUATION_DATE, positions, risk_df, NAV, valuation_date: str | None = None, export_id: str | None = None):
    if valuation_date is None:
        valuation_date = VALUATION_DATE

    mask_long = risk_df['market_value_eur'] >= 0
    long_exp  = risk_df[mask_long]['market_value_eur'].sum()
    short_exp = risk_df[~mask_long]['market_value_eur'].sum()

    df = pd.DataFrame([
        ('Fund',           FUND_ID),
        ('Valuation Date', str(VALUATION_DATE)),
        ('Positions',      str(len(positions))),
        ('NAV (EUR)',      f'{NAV:,.0f}'),
        ('Asset Classes',  ', '.join(sorted(positions['asset_class'].unique()))),
        ('Long Exposure',  f'{long_exp:,.0f}'),
        ('Short Exposure', f'{short_exp:,.0f}' if short_exp != 0 else '—'),
    ], columns=['Metric', 'Value'])

    html = display_dark_table(
        df,
        caption='Fund Summary',
        col_align_override={'Value': 'right'},
        col_styles=None,
        col_widths={'Metric': '200px', 'Value': '200px'},
        date_str=valuation_date,
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Fund Summary')
        filename = f'{export_id}_{title_slug}'
        save_html_as_png(html, FUND_ID, filename)


def display_asset_class_weights_n_positions(breakdown, NAV):
    df = breakdown.reset_index().rename(columns={'asset_class': 'Asset Class'})

    totals = pd.DataFrame([{
        'Asset Class'      : 'Total / NAV',
        'market_value_eur' : NAV,
        'weight_pct'       : 100.0,
        'n_positions'      : df['n_positions'].sum(),
    }])
    df = pd.concat([df, totals], ignore_index=True)

    display_dark_table(
        df,
        caption='Asset Class Breakdown',
        fmt={
            'market_value_eur': '{:,.0f}',
            'weight_pct'      : '{:.1f}%',
            'n_positions'     : '{:.0f}',
        },
        highlight_rows=[len(df) - 1],
        col_widths={'Asset Class': '180px'},
    )


def display_leverage(risk_df, deriv_notional_commitment, commitment_exposure,
                     gross_limit=3.0, borrowings_eur=0.0):
    NAV = risk_df['market_value_eur'].sum()
    gross_leverage      = (risk_df['gross_exposure'].sum() + borrowings_eur) / NAV
    commitment_leverage = commitment_exposure / NAV

    all_classes = sorted(
        c for c in risk_df['asset_class'].unique() if c != 'Borrowing'
    )

    rows = []
    for ac in all_classes:
        gross_eur  = risk_df[risk_df['asset_class'] == ac]['gross_exposure'].sum()
        if ac == 'Cash':
            commit_eur = 0.0
        elif ac == 'FX':
            commit_eur = risk_df[
                (risk_df['asset_class'] == 'FX') & (risk_df['is_hedge'] == 0)
            ]['market_value_eur'].abs().sum()
        elif ac == 'Derivative':
            commit_eur = abs(deriv_notional_commitment)
        else:
            commit_eur = risk_df[risk_df['asset_class'] == ac]['market_value_eur'].abs().sum()
        rows.append({
            'asset_class' : ac,
            'gross_eur'   : gross_eur,
            'g×nav'       : gross_eur / NAV,
            'commit_eur'  : commit_eur,
            'c×nav'       : commit_eur / NAV,
        })

    if borrowings_eur > 0:
        rows.append({
            'asset_class' : 'Borrowing',
            'gross_eur'   : borrowings_eur,
            'g×nav'       : borrowings_eur / NAV,
            'commit_eur'  : borrowings_eur,
            'c×nav'       : borrowings_eur / NAV,
        })

    rows.append({
        'asset_class' : 'Total',
        'gross_eur'   : risk_df['gross_exposure'].sum() + borrowings_eur,
        'g×nav'       : gross_leverage,
        'commit_eur'  : commitment_exposure,
        'c×nav'       : commitment_leverage,
    })

    df = pd.DataFrame(rows)
    df = df.rename(columns={
        'g×nav': 'Gross\n(×NAV)',
        'c×nav': 'Commit\n(×NAV)',
    })
    total_idx = len(df) - 1

    status = 'OK' if gross_leverage <= gross_limit else 'BREACH'
    caption = (f'Leverage  —  Gross limit: {gross_limit:.0f}×  |  '
               f'Current: {gross_leverage:.2f}×  |  Status: {status}')

    display_dark_table(
        df,
        caption=caption,
        fmt={
            'gross_eur'       : '{:,.0f}',
            'Gross\n(×NAV)'   : '{:.2f}×',
            'commit_eur'      : '{:,.0f}',
            'Commit\n(×NAV)'  : '{:.2f}×',
        },
        col_styles={
            'Gross\n(×NAV)' : lambda v: C['red'] if isinstance(v, float) and v > gross_limit else None,
            'Commit\n(×NAV)': lambda v: C['red'] if isinstance(v, float) and v > 2.0 else None,
        },
        highlight_rows=[total_idx],
        col_widths={'asset_class': '160px'},
    )


def display_var_es(var_result: dict, valuation_date: str = None, fund_id: str | None = None, export_id: str | None = None):
    """
    Display VaR and ES from var_result dict.

    Auto-detects which metrics are present (historical vs parametric) based on dict keys.
    If both are present, displays both in a single table.
    Extracts nav, horizon, and valuation_date from var_result.

    Parameters
    ----------
    var_result : dict
        Dictionary containing VaR/ES metrics from compute_fixed_position_var_1day()
        Must include: nav_eur, var_result metadata (horizon, etc.)
    valuation_date : str, optional
        Override valuation_date from var_result (for display only)
    export_id : str or None, default None
        If provided, save rendered HTML as PNG
    """
    nav = var_result.get('nav_eur', 0)
    horizon = var_result.get('horizon', 20)
    display_date = valuation_date or var_result.get('valuation_date')

    _c = ['Metric', '1D\n(% NAV)', f'{horizon}D\n(% NAV)', '1D\n(EUR)', f'{horizon}D\n(EUR)']
    rows = []

    # Check for historical metrics
    if 'var_hist_pct' in var_result:
        var_1d = var_result.get('var_hist_pct', 0)
        var_scaled = var_result.get('var_hist_scaled_pct', 0)
        es_1d = var_result.get('es_hist_pct', 0)
        es_scaled = var_result.get('es_hist_scaled_pct', 0)
        rows.append((f'VaR Historical', f'{var_1d*100:.2f}%',  f'{var_scaled*100:.2f}%',
                     f'{var_1d*nav:,.0f}',  f'{var_scaled*nav:,.0f}'))
        rows.append((f'ES Historical',  f'{es_1d*100:.2f}%',   f'{es_scaled*100:.2f}%',
                     f'{es_1d*nav:,.0f}',   f'{es_scaled*nav:,.0f}'))

    # Check for parametric metrics
    if 'var_param_pct' in var_result:
        var_1d = var_result.get('var_param_pct', 0)
        var_scaled = var_result.get('var_param_scaled_pct', 0)
        es_1d = var_result.get('es_param_pct', 0)
        es_scaled = var_result.get('es_param_scaled_pct', 0)
        rows.append((f'VaR Parametric', f'{var_1d*100:.2f}%',  f'{var_scaled*100:.2f}%',
                     f'{var_1d*nav:,.0f}',  f'{var_scaled*nav:,.0f}'))
        rows.append((f'ES Parametric',  f'{es_1d*100:.2f}%',   f'{es_scaled*100:.2f}%',
                     f'{es_1d*nav:,.0f}',   f'{es_scaled*nav:,.0f}'))

    df = pd.DataFrame(rows, columns=_c)
    caption = 'VaR & Expected Shortfall'
    html = display_dark_table(
        df,
        caption=caption,
        col_align_override={c: 'right' for c in _c[1:]},
        date_str=display_date,
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('VaR & Expected Shortfall')
        # Use provided fund_id parameter, or fallback to var_result
        fid = fund_id or var_result.get('fund_id', 'unknown')
        filename = f'{export_id}_{title_slug}'
        save_html_as_png(html, fid, filename)

def display_backtest_report(report, window_size=250, valuation_date: str | None = None, model: str = "Historical", fund_id: str | None = None, export_id: str | None = None):
    rep = report.copy()
    rep['breach_rate'] = rep['breach_rate'] * 100
    rep['expected']    = rep['expected'] * 100

    # Replace "Fixed-Position" (case-insensitive) with the provided model parameter
    import re
    rep['model'] = rep['model'].str.replace(r'fixed-position', model, regex=True, case=False)

    rep_filter = rep[['model', 'confidence', 'n_obs', 'n_breaches',
                       'breach_rate', 'expected',
                       'kupiec_p', 'christoffersen_p', 'result']].rename(columns={
        'kupiec_p'        : 'kupiec_pvalue',
        'christoffersen_p': 'christoffersen_pvalue',
        'n_obs'           : 'qtd_obs',
        'n_breaches'      : 'qtd_breaches',
    })

    # Build metadata with window size
    metadata_str = f'{window_size}d window' if valuation_date else None
    if valuation_date and metadata_str:
        date_label_str = f'As of {valuation_date} | {metadata_str}'
    else:
        date_label_str = valuation_date

    html = display_dark_table(
        rep_filter,
        caption='VaR Backtest Report',
        fmt={
            'breach_rate'           : '{:.2f}%',
            'expected'              : '{:.2f}%',
            'kupiec_p_value'        : '{:.4f}',
            'christoffersen_p_value': '{:.4f}',
        },
        col_styles={
            'result': lambda v: (
                C['green'] if str(v).upper() == 'PASS'
                else C['red']
            ),
        },
        col_widths={'model': '100px'},
        date_str=date_label_str,
        date_label='',
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('VaR Backtest Report')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)



def display_esma_report(n, breach_rate, zone):
    zone_color = {'green': C['green'], 'amber': C['amber'], 'red': C['red']}
    df = pd.DataFrame([
        ('Window',       'Last 250 trading days'),
        ('Breaches',     str(n)),
        ('Breach rate',  f'{breach_rate*100:.2f}%  (expected 1.0%)'),
        ('ESMA zone',    zone),
    ], columns=['Metric', 'Value'])
    display_dark_table(
        df,
        caption='ESMA Backtest Report',
        col_styles={'Value': lambda v: zone_color.get(v.lower(), None) if v.lower() in zone_color else None},
        col_align_override={'Value': 'right'},
        col_widths={'Metric': '200px', 'Value': '250px'},
    )


def display_lvar(lvar_result, NAV, valuation_date: str | None = None, fund_id: str | None = None, export_id: str | None = None):
    kpi = pd.DataFrame([
        ('VaR (1d 99%)',   f'{lvar_result["var"]*100:.2f}%',
         f'{lvar_result["var"]*NAV:,.0f}'),
        ('Liquidity cost', f'{lvar_result["liquidity_cost"]*100:.2f}%',
         f'{lvar_result["liquidity_cost"]*NAV:,.0f}'),
        ('LVaR (1d 99%)',  f'{lvar_result["lvar"]*100:.2f}%',
         f'{lvar_result["lvar"]*NAV:,.0f}'),
        ('LVaR increase',  f'+{lvar_result["lvar_pct_increase"]:.1f}%', ''),
    ], columns=['Metric', '% NAV', 'EUR'])
    html = display_dark_table(
        kpi,
        caption='Liquidity-Adjusted VaR',
        col_align_override={'% NAV': 'right', 'EUR': 'right'},
        col_widths={'Metric': '200px'},
        date_str=valuation_date,
        date_label='Valuation Date',
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Liquidity-Adjusted VaR')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)

    bac = lvar_result['by_asset_class']
    html2 = display_dark_table(
        bac,
        caption='LVaR by Asset Class',
        fmt={'market_value_eur': '{:,.0f}', 'liquidity_cost': '{:,.0f}'},
        date_str=valuation_date,
        date_label='Valuation Date',
        return_html=True,
    )

    display(HTML(html2))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('LVaR by Asset Class')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html2, fid, filename)


def display_granular(granular, NAV, valuation_date: str | None = None, fund_id: str | None = None, export_id: str | None = None):
    # prt.print_granular mutates the input in-place (formats strings).
    # Always work on a fresh numeric copy.
    granular = granular.copy()
    if isinstance(granular.index, pd.MultiIndex):
        granular = granular.reset_index()
    for col in ('gross_eur', 'gross_x_nav'):
        if col in granular.columns and not pd.api.types.is_numeric_dtype(granular[col]):
            granular[col] = pd.to_numeric(
                granular[col].astype(str).str.replace(',', '').str.replace('x', ''),
                errors='coerce',
            )

    total_gross = granular['gross_eur'].sum()

    # listed vs OTC
    lot = granular.groupby('listed_otc')['gross_eur'].sum().reset_index()
    lot.columns = ['Category', 'gross_eur']
    lot[_xnav()]    = lot['gross_eur'] / NAV
    lot['pct_leverage'] = lot['gross_eur'] / total_gross * 100
    lot = pd.concat([lot, pd.DataFrame([{
        'Category': 'Total', 'gross_eur': total_gross,
        _xnav(): total_gross / NAV, 'pct_leverage': 100.0,
    }])], ignore_index=True)
    html = display_dark_table(
        lot, caption='Leverage by Listed / OTC',
        fmt={'gross_eur': '{:,.0f}', _xnav(): '{:.2f}×', 'pct_leverage': '{:.1f}%'},
        highlight_rows=[len(lot) - 1],
        date_str=valuation_date,
        return_html=True,
    )
    display(HTML(html))
    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Leverage by Listed / OTC')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)

    # by source
    src = granular.groupby('source')['gross_eur'].sum().reset_index()
    src.columns = ['Source', 'gross_eur']
    src[_xnav()]    = src['gross_eur'] / NAV
    src['pct_leverage'] = src['gross_eur'] / total_gross * 100
    src = pd.concat([src, pd.DataFrame([{
        'Source': 'Total', 'gross_eur': total_gross,
        _xnav(): total_gross / NAV, 'pct_leverage': 100.0,
    }])], ignore_index=True)
    html = display_dark_table(
        src, caption='Leverage by Source',
        fmt={'gross_eur': '{:,.0f}', _xnav(): '{:.2f}×', 'pct_leverage': '{:.1f}%'},
        highlight_rows=[len(src) - 1],
        date_str=valuation_date,
        return_html=True,
    )
    display(HTML(html))
    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Leverage by Source')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)

    # granular detail
    detail = granular[['asset_class', 'sub_asset_class', 'source', 'listed_otc',
                        'gross_eur', 'gross_x_nav', 'n_positions']].copy()
    detail = detail.rename(columns={'gross_x_nav': _xnav('Gross')})
    html = display_dark_table(
        detail, caption='AIFMD II Granular Leverage Breakdown',
        fmt={'gross_eur': '{:,.0f}', _xnav('Gross'): '{:.2f}×', 'n_positions': '{:.0f}'},
        date_str=valuation_date,
        return_html=True,
    )
    display(HTML(html))
    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('AIFMD II Granular Leverage Breakdown')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)


def display_buckets(bucket_full, risk_df_liq, NAV, valuation_date: str | None = None, fund_id: str | None = None, export_id: str | None = None):
    total_abs = risk_df_liq['market_value_eur'].abs().sum()
    total_net = risk_df_liq['market_value_eur'].sum()
    totals = pd.DataFrame([{
        'liquidity_bucket': 'Total',
        'market_value_eur': total_net,
        'abs_exposure'    : total_abs,
        'pct_nav_net'     : total_net / NAV * 100,
        'pct_nav_abs'     : total_abs / NAV * 100,
        'n_positions'     : bucket_full['n_positions'].sum(),
    }])
    df = pd.concat([bucket_full, totals], ignore_index=True)
    html = display_dark_table(
        df,
        caption='Liquidity Profile — AIFMD Annex IV Buckets',
        fmt={
            'market_value_eur': '{:,.0f}',
            'abs_exposure'    : '{:,.0f}',
            'pct_nav_net'     : '{:.1f}%',
            'pct_nav_abs'     : '{:.1f}%',
            'n_positions'     : '{:.0f}',
        },
        highlight_rows=[len(df) - 1],
        date_str=valuation_date,
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Liquidity Profile — AIFMD Annex IV Buckets')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)


def display_inv_concentration(NAV, risk_df_liq, _investors, _conc, _top, _type):
    """Render investor concentration as a hand-built HTML table with colspan support."""
    flag_s = '⚠ ESMA flag'  if _conc['concentration_flag']  else '✓ OK'
    flag_3 = '⚠ High conc.' if _conc['high_concentration']  else '✓ OK'

    _r4 = redemption_stress(risk_df_liq, NAV,
                            redemption_pct=_conc['largest_investor_pct'], notice_days=5)
    _gap = (f"+{_r4['liquidity_gap_eur']/1e6:.1f}M"
            if _r4['liquidity_gap_eur'] >= 0
            else f"{_r4['liquidity_gap_eur']/1e6:.1f}M")

    # — shared styles ——————————————————————————————————————————————
    _BG_E   = '#1a1f2e'   # even row
    _BG_O   = '#141929'   # odd row
    _BG_SEP = '#36394F'   # section separator
    _BG_HDR = '#2F3245'   # thead
    _TXT    = '#9ca3af'   # muted body text
    _HDR_C  = '#a5cfdf'   # thead text
    _SEP_C  = '#587580'   # separator text
    _BORDER = '1px solid #0f1729'
    _FONT   = 'font-family:Arial,sans-serif;font-size:11px;'
    _PAD    = 'padding:5px 12px;'

    def _td(text, align='left', color=_TXT, bold=False, colspan=1):
        fw = 'bold' if bold else 'normal'
        cs = f' colspan="{colspan}"' if colspan > 1 else ''
        return (f'<td{cs} style="{_FONT}{_PAD}text-align:{align};'
                f'color:{color};font-weight:{fw};border-bottom:{_BORDER};">'
                f'{text}</td>')

    def _sep_row(label):
        return (f'<tr style="background:{_BG_SEP};">'
                f'<td colspan="5" style="{_FONT}padding:5px 12px;color:{_SEP_C};'
                f'font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;'
                f'text-align:left;border-bottom:{_BORDER};">{label}</td></tr>')

    def _spacer(n):
        bg = _BG_E if n % 2 == 0 else _BG_O
        return (f'<tr style="background:{bg};">'
                f'<td colspan="5" style="padding:3px;border-bottom:{_BORDER};"></td></tr>')

    # — build HTML ————————————————————————————————————————————————
    rows_html = []

    # thead
    headers = ['#', 'INVESTOR', 'TYPE', 'AUM (EUR)', '% NAV']
    th = ''.join(
        f'<th style="{_FONT}background:{_BG_HDR};padding:6px 12px;color:{_HDR_C};'
        f'text-align:{"center" if i==0 else "left" if i<3 else "right"};'
        f'font-weight:bold;letter-spacing:0.05em;border-bottom:2px solid #0f1729;">{h}</th>'
        for i, h in enumerate(headers)
    )
    thead = f'<thead><tr>{th}</tr></thead>'

    # investor ranking rows
    for i, (_, row) in enumerate(_top.reset_index(drop=True).iterrows(), 1):
        bg = _BG_E if i % 2 == 1 else _BG_O
        aum_c = f'{row["aum_eur"]:,.0f}'
        pct_c = f'{row["pct_nav"]*100:.1f}%'
        typ   = _type.get(row['investor_id'], '')
        rows_html.append(
            f'<tr style="background:{bg};">'
            + _td(str(i), 'center')
            + _td(row['investor_name'], 'left')
            + _td(typ, 'left')
            + _td(aum_c, 'right')
            + _td(pct_c, 'right')
            + '</tr>'
        )

    n = len(_top)

    # — concentration flags —
    rows_html.append(_spacer(n)); n += 1
    rows_html.append(_sep_row('ESMA THRESHOLDS: 20% SINGLE / 50% TOP-3'))

    def _flag_color(txt):
        return C['red'] if '⚠' in txt else C['green']

    for label, val in [
        ('Largest investor', f"{_conc['largest_investor_pct']*100:.1f}% NAV   {flag_s}"),
        ('Top 3 investors',  f"{_conc['top3_pct']*100:.1f}% NAV   {flag_3}"),
    ]:
        bg = _BG_E if n % 2 == 0 else _BG_O; n += 1
        rows_html.append(
            f'<tr style="background:{bg};">'
            + _td(f'&nbsp;&nbsp;{label}', 'left')
            + f'<td colspan="4" style="{_FONT}{_PAD}text-align:left;color:{_flag_color(val)};'
              f'font-weight:bold;border-bottom:{_BORDER};">{val}</td>'
            + '</tr>'
        )

    # — 5-day notice stress —
    rows_html.append(_spacer(n)); n += 1
    rows_html.append(_sep_row(f"5-DAY NOTICE STRESS  ({_conc['largest_investor_pct']*100:.1f}% NAV)"))

    for label, val in [
        ('Redemption',    f"EUR {_r4['redemption_amount_eur']:,.0f}"),
        ('Liquid assets', f"EUR {_r4['liquid_assets_eur']:,.0f}"),
        ('Gap / Coverage',f"{_gap}   {_r4['coverage_ratio']:.2f}×"),
        ('Action',        _r4['recommendation']),
    ]:
        bg = _BG_E if n % 2 == 0 else _BG_O; n += 1
        rows_html.append(
            f'<tr style="background:{bg};">'
            + _td(f'&nbsp;&nbsp;{label}', 'left')
            + f'<td colspan="4" style="{_FONT}{_PAD}text-align:left;color:{_TXT};'
              f'border-bottom:{_BORDER};">{val}</td>'
            + '</tr>'
        )

    # — monitoring recommendation —
    rows_html.append(_spacer(n)); n += 1
    rows_html.append(_sep_row('MONITORING RECOMMENDATION'))

    notes = []
    if _conc['high_concentration']:
        notes.append('— Enhanced monitoring: top-3 investors represent significant co-ordinated exit risk')
        notes.append('— Maintain liquidity buffer ≥ largest investor AUM')
    if _conc['concentration_flag']:
        notes.append(f"— Gate-trigger review: largest investor at {_conc['largest_investor_pct']*100:.1f}% NAV")
    if not notes:
        notes.append('— No immediate action. Continue quarterly investor concentration monitoring.')

    for note in notes:
        bg = _BG_E if n % 2 == 0 else _BG_O; n += 1
        rows_html.append(
            f'<tr style="background:{bg};">'
            f'<td colspan="5" style="{_FONT}{_PAD}text-align:left;color:{_TXT};'
            f'border-bottom:{_BORDER};">&nbsp;&nbsp;{note}</td>'
            '</tr>'
        )

    caption_html = (
        f'<caption style="color:{C["cyan"]};font-size:14px;font-weight:bold;'
        f'text-align:left;font-family:Helvetica Neue,Arial,sans-serif;'
        f'padding-bottom:8px;background:#1a2540;">Investor Concentration — NAV: EUR {NAV:,.0f}</caption>'
    )
    table = (
        f'<table style="border-collapse:collapse;width:100%;background:{_BG_E};">'
        f'{caption_html}{thead}<tbody>{"".join(rows_html)}</tbody></table>'
    )
    display(HTML(table))


def display_redemption_stress(
    fund_id,
    notice_days,
    redemption_scenarios,
    nav,
    risk_df_liq,
    valuation_date: str | None = None,
    export_id: str | None = None
):
    """
    Compute and display redemption stress scenarios.

    Parameters
    ----------
    fund_id : str
        Fund identifier
    notice_days : int
        Contractual notice period (days)
    redemption_scenarios : list of tuples
        [(pct, label), ...] e.g. [(0.10, 'Normal'), (0.25, 'Large')]
    nav : float
        Fund NAV in EUR
    risk_df_liq : pd.DataFrame
        Positions with liquidity_bucket column
    export_id : str or None, default None
        If provided, save rendered HTML as PNG
    """
    from src.risk.risk_utils import redemption_stress

    # Compute redemption stress for each scenario
    redstress = {}
    for _pct, _label in redemption_scenarios:
        _r = redemption_stress(risk_df_liq, nav, redemption_pct=_pct, notice_days=notice_days)
        _r['label'] = f'{_label} ({int(_pct*100)}%)'
        _r['gap'] = f"+{_r['liquidity_gap_eur']/1e6:.1f}M" if _r['liquidity_gap_eur'] >= 0 else f"{_r['liquidity_gap_eur']/1e6:.1f}M"
        redstress[_pct] = _r

    # Display
    rows = []
    for _, v in redstress.items():
        rows.append({
            'Scenario':       v['label'],
            'redemption_eur': v['redemption_amount_eur'],
            'liquid_eur':     v['liquid_assets_eur'],
            'gap':            v['gap'],
            'coverage':       v['coverage_ratio'],
            'Action':         v['recommendation'],
        })
    df = pd.DataFrame(rows)

    # Build metadata with NAV and notice
    metadata_parts = []
    if valuation_date:
        metadata_parts.append(f'As of {valuation_date}')
    metadata_parts.append(f'NAV: EUR {nav:,.0f}')
    metadata_parts.append(f'Notice: {notice_days}d')
    metadata_str = ' | '.join(metadata_parts)

    html = display_dark_table(
        df,
        caption=f'Redemption Stress — {fund_id}',
        fmt={'redemption_eur': '{:,.0f}', 'liquid_eur': '{:,.0f}', 'coverage': '{:.2f}x'},
        col_styles={'coverage': lambda v: C['green'] if isinstance(v, float) and v >= 1.0 else C['red']},
        date_str=metadata_str,
        date_label='',
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Redemption Stress')
        filename = f'{export_id}_{title_slug}'
        save_html_as_png(html, fund_id, filename)


def display_combined_stress_mkt_plus_liq(
    risk_df,
    risk_df_liq,
    nav,
    notice_days,
    delta_equity=-0.20,
    redemption_pct=0.25,
    valuation_date: str | None = None,
    fund_id: str | None = None,
    export_id: str | None = None,
):
    """
    Display combined stress scenario: market shock + simultaneous redemption.

    Stress test: equity market moves by delta_equity (e.g. -20%) AND
    investors simultaneously redeem redemption_pct of NAV.

    Parameters
    ----------
    risk_df : pd.DataFrame
        Risk-ready positions (for stress_equity computation)
    risk_df_liq : pd.DataFrame
        Positions with liquidity buckets (for liquid asset calculation)
    nav : float
        Fund NAV in EUR
    notice_days : int
        Contractual notice period (days)
    delta_equity : float, optional
        Equity market shock (e.g. -0.20 for -20%). Default -0.20.
    redemption_pct : float, optional
        Redemption as fraction of NAV (e.g. 0.25 for 25%). Default 0.25.
    export_id : str or None, default None
        If provided, save rendered HTML as PNG
    """
    from src.risk.risk_utils import stress_equity, redemption_stress

    # Market stress
    comb_eq = stress_equity(risk_df, delta_equity=delta_equity)
    comb_mkt_eur = comb_eq['stressed_pnl_eur']
    comb_nav_st = nav + comb_mkt_eur

    # Redemption stress at base redemption_pct
    base_red = redemption_stress(risk_df_liq, nav, redemption_pct=redemption_pct, notice_days=notice_days)

    # Combined: liquid assets shrink by market stress
    comb_liquid_st = base_red['liquid_assets_eur'] * (1 - abs(delta_equity))
    comb_redeem_eur = nav * redemption_pct
    comb_gap_st = comb_liquid_st - comb_redeem_eur
    comb_cov_st = comb_liquid_st / comb_redeem_eur if comb_redeem_eur > 0 else float('inf')
    comb_action = 'Can meet redemption' if comb_gap_st >= 0 else 'Gate / partial suspension required'

    # Display
    rows = [
        {'Metric': 'Market shock', 'Value': f'Equity {delta_equity*100:.0f}%', 'EUR': '', 'Status': ''},
        {'Metric': 'Stressed NAV (post-market)', 'Value': '', 'EUR': f'{comb_nav_st:,.0f}', 'Status': ''},
        {'Metric': '', 'Value': '', 'EUR': '', 'Status': ''},
        {'Metric': 'Redemption stress', 'Value': f'{redemption_pct*100:.0f}% NAV', 'EUR': f'{comb_redeem_eur:,.0f}', 'Status': ''},
        {'Metric': 'Liquid assets (post-market)', 'Value': '', 'EUR': f'{comb_liquid_st:,.0f}', 'Status': ''},
        {'Metric': 'Liquidity gap', 'Value': '', 'EUR': f'{comb_gap_st:,.0f}', 'Status': comb_action},
        {'Metric': 'Coverage ratio', 'Value': f'{comb_cov_st:.2f}x', 'EUR': '', 'Status': '✓ OK' if comb_cov_st >= 1.0 else '⚠ SHORTFALL'},
    ]

    df = pd.DataFrame(rows)

    # Build metadata with NAV
    metadata_parts = []
    if valuation_date:
        metadata_parts.append(f'As of {valuation_date}')
    metadata_parts.append(f'NAV: EUR {nav:,.0f}')
    metadata_str = ' | '.join(metadata_parts)

    html = display_dark_table(
        df,
        caption='Combined Stress Test — Market + Liquidity',
        col_styles={
            'Status': lambda v: (
                C['green'] if isinstance(v, str) and ('✓' in v or 'Can meet' in v) else
                C['red'] if isinstance(v, str) and ('⚠' in v or 'Gate' in v) else None
            )
        },
        date_str=metadata_str,
        date_label='',
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Combined Stress Test — Market + Liquidity')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)


def display_counterparty_stress(NAV, valuation_date: str | None = None, fund_id: str | None = None, export_id: str | None = None, **kwargs):
    """
    Display counterparty stress table.

    Parameters
    ----------
    NAV : float
        Net asset value.
    valuation_date : str, optional
        Valuation date for display.
    export_id : str or None, default None
        If provided, save rendered HTML as PNG
    **kwargs : dict
        Expected keys: 'cp_df', 'worst_cp', 'loss_eur', 'loss_pct'.
        Or pass individual arguments: cp_df, worst_cp, loss_eur, loss_pct.
    """
    # Handle both dict unpacking and individual arguments
    _cp_hf = kwargs.get('cp_df')
    _worst_cp = kwargs.get('worst_cp')
    _cp_loss_eur = kwargs.get('loss_eur')
    _cp_loss_pct = kwargs.get('loss_pct')

    status  = '⚠ BREACH' if _cp_loss_pct > 0.05 else '✓ Within limit'

    # Pre-format all numeric columns as strings so summary rows stay blank.
    cp = _cp_hf[['counterparty', 'type', 'exposure_eur',
                  'collateral_eur', 'net_exposure_eur', 'loss_pct_nav']].copy()
    cp['exposure_eur']     = cp['exposure_eur'].map('{:,.0f}'.format)
    cp['collateral_eur']   = cp['collateral_eur'].map('{:,.0f}'.format)
    cp['net_exposure_eur'] = cp['net_exposure_eur'].map('{:,.0f}'.format)
    cp['loss_pct_nav_raw'] = cp['loss_pct_nav']          # keep raw for color fn
    cp['loss_pct_nav']     = cp['loss_pct_nav'].map('{:.1%}'.format)

    def _srow(**kw):
        base = {c: '' for c in cp.columns}
        base['loss_pct_nav_raw'] = float('nan')
        base.update(kw)
        return base

    # blank spacer + separator row
    cp = pd.concat([cp, pd.DataFrame([
        _srow(),
        _srow(counterparty='WORST-CASE DEFAULT SCENARIO'),
        _srow(counterparty='  Counterparty',               type=_worst_cp['counterparty']),
        _srow(counterparty='  Net loss (post-collateral)', type=f"EUR {_cp_loss_eur:,.0f}"),
        _srow(counterparty='  % of NAV',                  type=f'{_cp_loss_pct*100:.1f}%'),
        _srow(counterparty='  AIFMD limit',               type='5% NAV  (EU 231/2013 Art. 43)'),
        _srow(counterparty='  Status',                    type=status),
    ])], ignore_index=True)

    sep_idx = len(_cp_hf) + 1   # +1 for the blank spacer row

    # Build metadata with NAV
    metadata_parts = []
    if valuation_date:
        metadata_parts.append(f'As of {valuation_date}')
    metadata_parts.append(f'NAV: EUR {NAV:,.0f}')
    metadata_str = ' | '.join(metadata_parts)

    html = display_dark_table(
        cp.drop(columns=['loss_pct_nav_raw']),
        caption='Counterparty Register',
        highlight_rows=[sep_idx],
        col_styles={
            'loss_pct_nav': lambda v: (
                C['red']   if isinstance(v, str) and '⚠' in v else
                C['green'] if isinstance(v, str) and '✓' in v else None
            ),
            'type': lambda v: (
                C['red']   if isinstance(v, str) and '⚠' in v else
                C['green'] if isinstance(v, str) and '✓' in v else None
            ),
        },
        date_str=metadata_str,
        date_label='',
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Counterparty Register')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)


def display_attribution(attr, flagged):
    df = pd.DataFrame([
        ('Attribution period',         f"{attr.index.min().date()} → {attr.index.max().date()}"),
        ('Days attributed',            str(len(attr))),
        ('Correlation (actual vs expl.)', f"{attr['pnl_actual'].corr(attr['pnl_explained']):.3f}"),
        ('Median % explained',         f"{attr['pct_explained'].median():.1%}"),
        ('Days ≥ 80% explained',       f"{(attr['pct_explained'] >= 0.80).sum()}  ({(attr['pct_explained'] >= 0.80).mean():.1%})"),
        ('Residual vol (EUR)',          f"{attr['pnl_residual'].std():,.0f}"),
        ('Residual / total vol',        f"{attr['pnl_residual'].std() / attr['pnl_actual'].std():.1%}"),
        ('Flagged days',               f"{len(flagged)}  ({len(flagged)/len(attr):.1%})"),
    ], columns=['Metric', 'Value'])
    display_dark_table(
        df,
        caption='P&L Attribution Summary',
        col_align_override={'Value': 'right'},
        col_widths={'Metric': '260px', 'Value': '200px'},
    )


def display_historical_scenarios(historical_scenarios: dict, fund_id: str | None = None, export_id: str | None = None):
    """Render the HISTORICAL_SCENARIOS parameter table (shock definitions, not results)."""
    rows = []
    for _, p in historical_scenarios.items():
        rows.append({
            'Scenario'    : p['name'],
            'Equity'      : f"{p['delta_equity']*100:.0f}%",
            'Rates (bps)' : f"{p['delta_y']*10000:.0f}",
            'Credit (bps)': f"+{p['delta_spread']*10000:.0f}",
            'USD'         : f"{p['fx_shocks'].get('USD', 0)*100:+.0f}%",
            'GBP'         : f"{p['fx_shocks'].get('GBP', 0)*100:+.0f}%",
        })
    df = pd.DataFrame(rows)
    html = display_dark_table(
        df,
        caption='Historical Stress Scenarios — Shock Parameters',
        col_styles={
            'Equity'      : lambda v: C['red']   if isinstance(v, str) and v.startswith('-') else C['green'],
            'Rates (bps)' : lambda v: C['amber'] if isinstance(v, str) and v not in ('0', '+0') else None,
            'Credit (bps)': lambda v: C['amber'] if isinstance(v, str) and v not in ('0', '+0') else None,
            'USD'         : lambda v: C['red']   if isinstance(v, str) and v.startswith('-') else None,
            'GBP'         : lambda v: C['red']   if isinstance(v, str) and v.startswith('-') else None,
        },
        col_widths={'Scenario': '260px'},
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Historical Stress Scenarios — Shock Parameters')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)


def display_scenarios(risk_df, custom: dict | None = None, add_historical: bool = False, valuation_date: str | None = None, fund_id: str | None = None, export_id: str | None = None):
    """Render stress scenario P&L results — custom and/or historical."""
    from src.risk.risk_utils import HISTORICAL_SCENARIOS, stress_historical
    NAV  = risk_df['market_value_eur'].sum()
    rows = []

    if custom:
        for label, result in custom.items():
            rows.append({
                'Scenario': label,
                'pnl_eur' : result['stressed_pnl_eur'],
                'pct_nav' : result['stressed_pnl_eur'] / NAV * 100,
            })

    if add_historical:
        for key, params in HISTORICAL_SCENARIOS.items():
            result = stress_historical(risk_df, key)
            rows.append({
                'Scenario': params['name'],
                'pnl_eur' : result['stressed_pnl_eur'],
                'pct_nav' : result['stressed_pnl_eur'] / NAV * 100,
            })

    df      = pd.DataFrame(rows)
    worst   = df['pnl_eur'].idxmin()

    html = display_dark_table(
        df,
        caption='Stress Scenario Results',
        fmt={
            'pnl_eur': '{:,.0f}',
            'pct_nav': '{:.2f}%',
        },
        col_styles={
            'pnl_eur': lambda v: C['red']   if isinstance(v, float) and v < 0 else C['green'],
            'pct_nav': lambda v: C['red']   if isinstance(v, float) and v < 0 else C['green'],
        },
        highlight_rows=[worst],
        col_widths={'Scenario': '260px'},
        date_str=valuation_date,
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Stress Scenario Results')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)
def display_ptc(result: dict, test_number: int | None = None,
                col_widths_trade: dict | None = None,
                col_widths_metrics: dict | None = None,
                col_widths_breaches: dict | None = None,
                valuation_date: str | None = None,
                fund_id: str | None = None,
                export_id: str | None = None,
                return_html: bool = False) -> str | None:
    """Render pre-trade check as 3 separate independent tables.

    Table 1 (Trade Details): 4 columns
    Table 2 (Metrics): 3 columns (metric | pre-trade | post-trade)
    Table 3 (Breaches): 2 columns

    Parameters
    ----------
    col_widths_trade : dict, optional
        Column widths for trade table: {'label': 'XXXpx', 'value': 'XXXpx', ...}
    col_widths_metrics : dict, optional
        Column widths for metrics table: {'metric': 'XXXpx', 'pre': 'XXXpx', 'post': 'XXXpx'}
    col_widths_breaches : dict, optional
        Column widths for breaches table: {'item': 'XXXpx', 'value': 'XXXpx'}
    return_html : bool, default False
        If True, return combined HTML string instead of displaying. If False, display in notebook.
    """
    from datetime import datetime, timedelta
    import pandas as pd

    t        = result['proposed_trade']
    notional = abs(t['quantity'] * t['price_eur'])
    status   = '✓  PASSED' if result['passed'] else '✗  FAILED'
    pre      = result.get('pre_trade_metrics', {})
    cap_txt  = (f'Pre-Trade Evaluation #{test_number}'
                if test_number is not None else 'Pre-Trade Evaluation')
    if valuation_date:
        cap_txt += f'<br><span style="font-size: 10px; font-weight: normal; color: #999;">Computed on {valuation_date}</span>'

    def _fmt(k: str, v) -> str:
        if not isinstance(v, float): return str(v)
        if v == 0.0: return '—'
        k = k.lower()
        if any(x in k for x in ('leverage', 'multiplier')): return f'{v:.2f}×'
        if any(x in k for x in ('exposure', 'bonds', 'net_eq', 'borrowing',
                                 'fx_exposure', 'notional', 'deriv_')): return f'{v:,.0f}'
        if 'pct' in k or 'var' in k: return f'{v:.2f}%'
        if v > 10_000: return f'{v:,.0f}'
        return f'{v:.2f}'

    # Shared styles
    _BG_E   = '#1a1f2e'
    _BG_O   = '#141929'
    _BG_SEP = '#36394F'
    _TXT    = '#9ca3af'
    _SEP_C  = '#587580'
    _BORDER = '1px solid #0f1729'
    _FONT   = 'font-family:Arial,sans-serif;font-size:11px;'
    _PAD    = 'padding:5px 12px;'

    # ═════════════════════════════════════════════════════════════════════════
    # TABLE 1: TRADE DETAILS (4 columns)
    # ═════════════════════════════════════════════════════════════════════════

    if col_widths_trade is None:
        col_widths_trade = {'label1': '80px', 'value1': '50px', 'label2': '150px', 'value2': '100px'}

    # Compute settlement date
    val_date = pd.to_datetime(VALUATION_DATE)
    settlement_date = (val_date + timedelta(days=2)).strftime('%Y-%m-%d')
    counterparty = t.get('counterparty', '—')
    underlying_risk = t.get('underlying_risk', '—')

    trade_rows = []
    trade_data = [
        ('Fund', result['fund_id'], 'Trade Date', VALUATION_DATE),
        ('Trade', f"{t['direction'].upper()}  {t['quantity']:,} × {t['isin']}", 'Settlement', settlement_date),
        ('Notional', f"EUR {notional:,.0f}   @   EUR {t['price_eur']:,.2f}", 'Counterparty', counterparty),
        ('Result', status, 'Underlying Risk', underlying_risk),
    ]

    result_color = C['green'] if '✓' in status else C['red']

    for label1, val1, label2, val2 in trade_data:
        bg = _BG_E if len(trade_rows) % 2 == 0 else _BG_O
        val1_color = result_color if label1 == 'Result' else _TXT
        trade_rows.append(
            f'<tr style="background:{bg};">'
            f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:right;border-bottom:{_BORDER};">{label1}</td>'
            f'<td style="{_FONT}{_PAD}color:{val1_color};text-align:left;border-bottom:{_BORDER};">{val1}</td>'
            f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:right;border-bottom:{_BORDER};">{label2}</td>'
            f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:left;border-bottom:{_BORDER};">{val2}</td>'
            '</tr>'
        )

    colgroup_trade = (
        f'<colgroup>'
        f'<col style="width:{col_widths_trade["label1"]};"><col style="width:{col_widths_trade["value1"]};"> '
        f'<col style="width:{col_widths_trade["label2"]};"><col style="width:{col_widths_trade["value2"]};"> '
        f'</colgroup>'
    )

    table1_html = (
        f'<table style="border-collapse:collapse;width:auto;table-layout:fixed;background:{_BG_E};">'
        f'<caption style="color:{C["cyan"]};font-size:14px;font-weight:bold;text-align:left;'
        f'font-family:Helvetica Neue,Arial,sans-serif;padding-bottom:8px;background:#1a2540;">{cap_txt}</caption>'
        f'{colgroup_trade}'
        f'<tbody>'
        f'<tr style="background:{_BG_SEP};"><td colspan="4" style="{_FONT}{_PAD}color:{_SEP_C};font-weight:bold;'
        f'letter-spacing:0.05em;text-transform:uppercase;text-align:left;border-bottom:{_BORDER};">FUND AND TRADE DETAILS</td></tr>'
        f'{"".join(trade_rows)}'
        f'</tbody></table>'
    )

    # ═════════════════════════════════════════════════════════════════════════
    # TABLE 2: METRICS (3 columns)
    # ═════════════════════════════════════════════════════════════════════════

    if col_widths_metrics is None:
        col_widths_metrics = {'metric': '120px', 'pre': '150px', 'post': '130px'}

    # Limit thresholds for breach detection
    _LIMITS = {
        'gross_leverage': 3.0,
        'commitment_leverage': 2.0,
        'max_issuer_pct': 25.0,
        'trade_issuer_pct': 25.0,
        'max_sector_pct': 30.0,
        'trade_sector_pct': 30.0,
        'max_net_short_pct': 0.2,
        'wtd_avg_days_to_liquidate': 30.0,
    }

    metrics_rows = []
    for k, v in result['post_trade_metrics'].items():
        bg = _BG_E if len(metrics_rows) % 2 == 0 else _BG_O
        pre_fmt = _fmt(k, pre[k]) if k in pre else ''
        post_fmt = _fmt(k, v)

        # Check if pre-trade metric breached limit
        pre_color = _TXT
        pre_breached = False
        if pre_fmt and k in _LIMITS:
            try:
                pre_val = float(pre[k])
                if pre_val > _LIMITS[k]:
                    pre_fmt = f'⚠ {pre_fmt}'
                    pre_color = '#fbbf24'  # yellow for pre-existing breach
                    pre_breached = True
            except (ValueError, TypeError, KeyError):
                pass

        # Check if post-trade metric breached limit
        post_breached = False
        if k in _LIMITS:
            try:
                post_val = float(v)
                post_breached = post_val > _LIMITS[k]
            except (ValueError, TypeError, KeyError):
                pass

        # Detect changes
        changed = (pre_fmt != post_fmt) and pre_fmt != ''

        # Determine if metric improved (for "lower is better" metrics)
        improved = False
        if changed and not post_breached:
            try:
                pre_val = float(str(pre[k]))
                post_val = float(v)
                # Lower is better for: concentrations, short exposure, days to liquidate, leverage
                lower_is_better = any(
                    x in k.lower() for x in ('pct', 'leverage', 'exposure', 'short', 'days')
                )
                improved = (post_val < pre_val) if lower_is_better else False
            except (ValueError, TypeError, KeyError):
                improved = False

        # Determine if breach worsened (for metrics where higher is worse)
        worsened = False
        if pre_breached and post_breached and changed:
            try:
                pre_val = float(pre[k])
                post_val = float(v)
                # For concentrations/leverage, higher is worse
                worsened = post_val > pre_val
            except (ValueError, TypeError, KeyError):
                worsened = False

        # Apply styling based on breach status — bold only if value changed
        if pre_breached and post_breached:
            if worsened:
                # Breach worsened — red + bold
                post_color = C['red']
                post_weight = 'font-weight:bold;' if changed else ''
            else:
                # Breach continued but not worse — yellow, no bold, with ⚠
                post_fmt = f'⚠ {post_fmt}'
                post_color = '#fbbf24'
                post_weight = ''
        elif not pre_breached and post_breached:
            # New breach — red + bold
            post_color = C['red']
            post_weight = 'font-weight:bold;'
        elif changed:
            # Changed (improved or just changed, no breach) — white + bold
            post_color = '#ffffff'
            post_weight = 'font-weight:bold;'
        else:
            # Unchanged — normal
            post_color = _TXT
            post_weight = ''

        metrics_rows.append(
            f'<tr style="background:{bg};">'
            f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:left;border-bottom:{_BORDER};">&nbsp;&nbsp;{k}</td>'
            f'<td style="{_FONT}{_PAD}color:{pre_color};text-align:right;border-bottom:{_BORDER};">{pre_fmt}</td>'
            f'<td style="{_FONT}{_PAD}color:{post_color};{post_weight}text-align:right;border-bottom:{_BORDER};">{post_fmt}</td>'
            '</tr>'
        )

    colgroup_metrics = (
        f'<colgroup>'
        f'<col style="width:{col_widths_metrics["metric"]};"><col style="width:{col_widths_metrics["pre"]};"><col style="width:{col_widths_metrics["post"]};"> '
        f'</colgroup>'
    )

    table2_html = (
        f'<table style="border-collapse:collapse;width:auto;table-layout:fixed;background:{_BG_E};margin-top:15px;">'
        f'{colgroup_metrics}'
        f'<tbody>'
        f'<tr style="background:{_BG_SEP};"><td style="{_FONT}{_PAD}color:{_SEP_C};font-weight:bold;'
        f'letter-spacing:0.05em;text-transform:uppercase;text-align:left;border-bottom:{_BORDER};">METRICS</td>'
        f'<td style="{_FONT}{_PAD}color:{_SEP_C};font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;'
        f'text-align:right;border-bottom:{_BORDER};">PRE-TRADE</td>'
        f'<td style="{_FONT}{_PAD}color:{_SEP_C};font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;'
        f'text-align:right;border-bottom:{_BORDER};">POST-TRADE</td></tr>'
        f'{"".join(metrics_rows)}'
        f'</tbody></table>'
    )

    # ═════════════════════════════════════════════════════════════════════════
    # TABLE 3: BREACHES & PRE-EXISTING LIMITS
    # ═════════════════════════════════════════════════════════════════════════

    if col_widths_breaches is None:
        col_widths_breaches = {'item': '100px', 'value': '350px'}

    # Detect pre-existing breaches in concentration metrics
    pre_existing_sector_breaches = []
    pre_existing_issuer_breaches = []

    # Check sector breaches from pre-trade exposures
    sector_exp_pre = result.get('sector_exposures_pre', {})
    for sector, pct in sector_exp_pre.items():
        if pct > 30.0:
            pre_existing_sector_breaches.append(f"{sector}: {pct:.1f}%")

    # Check issuer breaches from pre-trade exposures
    issuer_exp_pre = result.get('issuer_exposures_pre', {})
    for issuer, pct in issuer_exp_pre.items():
        if pct > 25.0:
            pre_existing_issuer_breaches.append(f"{issuer}: {pct:.1f}%")

    breaches_rows = []

    if result['breaches']:
        # Trade caused new breaches — show in red
        for b in result['breaches']:
            breaches_rows.append(
                f'<tr style="background:{_BG_SEP};"><td colspan="2" style="{_FONT}{_PAD}color:{C["red"]};'
                f'font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;text-align:left;border-bottom:{_BORDER};">✗&nbsp;{b["check"]}</td></tr>'
            )
            for label, value in [
                ('Limit', f"{b['limit']}{b['unit']}"),
                ('Post Trade', f"{float(b['actual']):.1f}{b['unit']}"),
                ('Detail', b['message']),
            ]:
                bg = _BG_E if len(breaches_rows) % 2 == 0 else _BG_O
                breaches_rows.append(
                    f'<tr style="background:{bg};">'
                    f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:left;border-bottom:{_BORDER};">&nbsp;&nbsp;&nbsp;&nbsp;{label}</td>'
                    f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:left;border-bottom:{_BORDER};">{value}</td>'
                    '</tr>'
                )
    else:
        # Trade approved — check if there are pre-existing breaches
        if pre_existing_sector_breaches or pre_existing_issuer_breaches:
            # Yellow — approved but pre-existing breaches
            status_color = '#fbbf24'  # yellow
            status_text = 'TRADE APPROVED — verify no related breaches below'
        else:
            # Green — no breaches at all
            status_color = C['green']
            status_text = 'NO LIMIT BREACHES — TRADE APPROVED'

        breaches_rows.append(
            f'<tr style="background:{_BG_SEP};"><td colspan="2" style="{_FONT}{_PAD}color:{status_color};'
            f'font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;text-align:left;border-bottom:{_BORDER};">{status_text}</td></tr>'
        )

        # Show pre-existing breaches if any
        if pre_existing_sector_breaches:
            bg = _BG_E if len(breaches_rows) % 2 == 0 else _BG_O
            breaches_rows.append(
                f'<tr style="background:{bg};">'
                f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:left;border-bottom:{_BORDER};">Sector breaches</td>'
                f'<td style="{_FONT}{_PAD}color:#fbbf24;text-align:left;border-bottom:{_BORDER};">{", ".join(pre_existing_sector_breaches)}</td>'
                '</tr>'
            )

        if pre_existing_issuer_breaches:
            bg = _BG_E if len(breaches_rows) % 2 == 0 else _BG_O
            breaches_rows.append(
                f'<tr style="background:{bg};">'
                f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:left;border-bottom:{_BORDER};">Issuer/short breaches</td>'
                f'<td style="{_FONT}{_PAD}color:#fbbf24;text-align:left;border-bottom:{_BORDER};">{", ".join(pre_existing_issuer_breaches)}</td>'
                '</tr>'
            )

    colgroup_breaches = (
        f'<colgroup>'
        f'<col style="width:{col_widths_breaches["item"]};"><col style="width:{col_widths_breaches["value"]};"> '
        f'</colgroup>'
    )

    table3_html = (
        f'<table style="border-collapse:collapse;width:auto;table-layout:fixed;background:{_BG_E};margin-top:15px;">'
        f'{colgroup_breaches}'
        f'<tbody>'
        f'{"".join(breaches_rows)}'
        f'</tbody></table>'
    )

    # Combine all 3 tables into one HTML
    combined_html = table1_html + '<br>' + table2_html + '<br>' + table3_html

    # Return HTML if requested
    if return_html:
        return combined_html

    # Otherwise display in notebook
    display(HTML(table1_html))
    display(HTML(table2_html))
    display(HTML(table3_html))

    # Save as PNG if export_id is provided
    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Pre-Trade Check')
        filename = f'{export_id}_{title_slug}'
        save_html_as_png(combined_html, result.get('fund_id', 'unknown'), filename)


def display_asset_class_breakdown(df: pd.DataFrame, valuation_date: str | None = None, fund_id: str | None = None, export_id: str | None = None) -> None:
    """
    Display asset class breakdown with market value, position count, and weight.

    Parameters
    ----------
    df : pd.DataFrame
        Risk DataFrame with columns: asset_class, market_value_eur, isin.
    export_id : str or None, default None
        If provided, save rendered HTML as PNG

    Returns
    -------
    None
        Displays table via IPython.display.
    """
    # Compute NAV from DataFrame
    nav = float(df['market_value_eur'].sum())

    # Group by asset class
    breakdown = df.groupby('asset_class').agg(
        market_value_eur=('market_value_eur', 'sum'),
        n_positions=('isin', 'count'),
    ).sort_values('market_value_eur', ascending=False)

    breakdown['weight_pct'] = breakdown['market_value_eur'] / nav * 100

    # Format columns
    breakdown['market_value_eur'] = breakdown['market_value_eur'].map('{:,.0f}'.format)
    breakdown['weight_pct'] = breakdown['weight_pct'].map('{:.2f}%'.format)
    breakdown['n_positions'] = breakdown['n_positions'].map('{:d}'.format)

    # Rename for display
    breakdown.columns = ['Market Value (EUR)', '# Positions', '% NAV']

    html = display_dark_table(
        breakdown,
        caption='Asset Class Breakdown',
        col_align_override={'Asset Class': 'left',
                           'Market Value (EUR)': 'right',
                           '# Positions': 'right',
                           '% NAV': 'right'},
        date_str=valuation_date,
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify('Asset Class Breakdown')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)


def display_top_positions(df: pd.DataFrame, n_top: int = 100, valuation_date: str | None = None, fund_id: str | None = None, export_id: str | None = None) -> None:
    """
    Display top N positions as an HTML table with asset class, issuer, market value, and weight.

    Parameters
    ----------
    df : pd.DataFrame
        Risk DataFrame with columns: asset_class, issuer, market_value_eur.
    n_top : int
        Number of top positions to display. Default: 100.
    export_id : str or None, default None
        If provided, save rendered HTML as PNG

    Returns
    -------
    None
        Displays table via IPython.display.
    """
    # Compute NAV from DataFrame
    nav = float(df['market_value_eur'].sum())

    # Select available columns
    cols = ['asset_class', 'issuer', 'market_value_eur']
    available_cols = [col for col in cols if col in df.columns]

    # Sort by market value descending and take top N
    top_pos = df.nlargest(n_top, 'market_value_eur')[available_cols].copy()

    top_pos['weight_pct'] = top_pos['market_value_eur'] / nav * 100

    # Format columns
    top_pos['market_value_eur'] = top_pos['market_value_eur'].map('{:,.0f}'.format)
    top_pos['weight_pct'] = top_pos['weight_pct'].map('{:.2f}%'.format)

    # Rename for display
    col_names = {'asset_class': 'Asset Class', 'issuer': 'Issuer',
                 'market_value_eur': 'Market Value (EUR)', 'weight_pct': '% NAV'}
    top_pos.columns = [col_names.get(col, col) for col in top_pos.columns]

    # Align columns appropriately
    col_align = {col: 'left' if col in ['Asset Class', 'Issuer'] else 'right'
                 for col in top_pos.columns}

    html = display_dark_table(
        top_pos,
        caption=f'Top {n_top} Positions',
        col_align_override=col_align,
        date_str=valuation_date,
        return_html=True,
    )

    display(HTML(html))

    if export_id is not None:
        from src.ui.nb_utils import _slugify, save_html_as_png
        title_slug = _slugify(f'Top {n_top} Positions')
        filename = f'{export_id}_{title_slug}'
        fid = fund_id or 'unknown'
        save_html_as_png(html, fid, filename)


def display_counterparty_risk_ucits(NAV, _cp_ucits, _worst_cp, _cp_loss_eur, _cp_loss_pct):
    status = '⚠ BREACH' if _cp_loss_pct > 0.10 else '✓ Within limit'

    cp = _cp_ucits[['counterparty', 'type', 'exposure_eur',
                     'collateral_eur', 'net_exposure_eur', 'net_pct_nav']].copy()
    cp['exposure_eur']     = cp['exposure_eur'].map('{:,.0f}'.format)
    cp['collateral_eur']   = cp['collateral_eur'].map('{:,.0f}'.format)
    cp['net_exposure_eur'] = cp['net_exposure_eur'].map('{:,.0f}'.format)
    cp['net_pct_nav_raw']  = cp['net_pct_nav']
    cp['net_pct_nav']      = cp['net_pct_nav'].map('{:.1%}'.format)

    def _srow(**kw):
        base = {c: '' for c in cp.columns}
        base['net_pct_nav_raw'] = float('nan')
        base.update(kw)
        return base

    cp = pd.concat([cp, pd.DataFrame([
        _srow(),
        _srow(counterparty='WORST-CASE COUNTERPARTY DEFAULT'),
        _srow(counterparty='  Counterparty',                   type=_worst_cp['counterparty']),
        _srow(counterparty='  Net exposure (post-collateral)', type=f"EUR {_cp_loss_eur:,.0f}"),
        _srow(counterparty='  % of NAV',                      type=f'{_cp_loss_pct*100:.1f}%'),
        _srow(counterparty='  UCITS limit',                   type='10% NAV  (UCITS Dir. Art. 52)'),
        _srow(counterparty='  Status',                        type=status),
    ])], ignore_index=True)

    sep_idx = len(_cp_ucits) + 1

    display_dark_table(
        cp.drop(columns=['net_pct_nav_raw']),
        caption=f'Counterparty Exposure — NAV: EUR {NAV:,.0f}',
        highlight_rows=[sep_idx],
        col_styles={
            'net_pct_nav': lambda v: (
                C['red']   if isinstance(v, str) and '⚠' in v else
                C['green'] if isinstance(v, str) and '✓' in v else None
            ),
            'type': lambda v: (
                C['red']   if isinstance(v, str) and '⚠' in v else
                C['green'] if isinstance(v, str) and '✓' in v else None
            ),
        },
    )
