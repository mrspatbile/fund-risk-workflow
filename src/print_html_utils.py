from IPython.display import display, HTML
import re
import pandas as pd
from src.plot_style import C
from src.risk_utils import redemption_stress


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

    Notes
    -----
    - Index is always hidden.
    - Requires C (colour palette dict) from plot_style to be in scope.
    - ESG example: use ESG_COL_STYLES and ESG_FMT as col_styles and fmt.
    """
    
    _UPPER = {'Eur', 'Nav', 'Aum', 'Otc', 'Lcr', 'Rag', 'Dpi', 'Irr', 'Esg',
              'Env', 'Soc', 'Gov', 'Pai', 'Hhi', 'Pb', 'Id', 'Qtd'}

    def _fmt_col(col):
        col = col.replace('_', ' ').replace('pct', '%')
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
    col_styles_remapped = {col_map[k]: v for k, v in col_styles.items() if k in col_map} if col_styles else None
    fmt_remapped        = {col_map.get(k, k): v for k, v in fmt.items()} if fmt else None

    def _style(df):
        styles = []
        for i, row in df.iterrows():
            is_highlight   = highlight_rows and i in highlight_rows
            bg             = "#36394F" if is_highlight else ('#1a1f2e' if i % 2 == 0 else '#141929')
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

    table_styles = [
        {'selector': 'caption', 'props': [
            ('color',            C['cyan']),
            ('font-size',        '14px'),
            ('font-weight',      'bold'),
            ('text-align',       'left'),
            ('font-family',      'Helvetica Neue, Helvetica, Arial, sans-serif'),
            ('padding-bottom',   '8px'),
            ('background-color', '#1a2540'),
        ]},
        {'selector': 'thead th', 'props': [
            ('background-color', '#2F3245'),
            ('font-family',      'Arial, sans-serif'),
            ('font-size',        '10px'),
            ('font-weight',      'bold'),
            ('padding',          '6px 12px'),
            ('border-bottom',    '2px solid #0f1729'),
            ('color',            '#a5cfdf'),
            ('letter-spacing',   '0.05em'),
            ('text-transform',   'uppercase'),
            ('white-space',      'pre-wrap'),
        ]},
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
        styled = styled.set_caption(caption)
    if fmt_remapped:
        styled = styled.format(fmt_remapped, na_rep='—')

    styled = styled.hide(axis='index')
    display(styled)

#-------------------
# general info displays
#-------------------

def display_fund_summary(FUND_ID, VALUATION_DATE, positions, risk_df, NAV):
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

    display_dark_table(
        df,
        caption='Fund Summary',
        col_align_override={'Value': 'right'},
        col_styles=None,
        col_widths={'Metric': '200px', 'Value': '200px'},
    )


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


def display_var_es(var_1d, var_20d, es_1d, es_20d, NAV):
    # Column names are pre-set to their final display form so _fmt_col leaves them
    # unchanged. \n renders as a line break via white-space: pre-wrap on thead th.
    # (EUR) already contains '(eur)' so the EUR-detection block in _fmt_col is skipped.
    _c = ['Metric', '1D\n(% NAV)', '20D\n(% NAV)', '1D\n(EUR)', '20D\n(EUR)']
    df = pd.DataFrame([
        ('VaR Historical', f'{var_1d*100:.2f}%',  f'{var_20d*100:.2f}%',
         f'{var_1d*NAV:,.0f}',  f'{var_20d*NAV:,.0f}'),
        ('ES Historical',  f'{es_1d*100:.2f}%',   f'{es_20d*100:.2f}%',
         f'{es_1d*NAV:,.0f}',   f'{es_20d*NAV:,.0f}'),
    ], columns=_c)
    display_dark_table(
        df,
        caption='VaR & Expected Shortfall',
        col_align_override={c: 'right' for c in _c[1:]},
    )

def display_backtest_report(report, window_size=250):
    rep = report.copy()
    rep['breach_rate'] = rep['breach_rate'] * 100
    rep['expected']    = rep['expected'] * 100

    rep_filter = rep[['model', 'confidence', 'n_obs', 'n_breaches',
                       'breach_rate', 'expected',
                       'kupiec_p', 'christoffersen_p', 'result']].rename(columns={
        'kupiec_p'        : 'kupiec_pvalue',
        'christoffersen_p': 'christoffersen_pvalue',
        'n_obs'           : 'qtd_obs',
        'n_breaches'      : 'qtd_breaches',
    })

    display_dark_table(
        rep_filter,
        caption=f'VaR Backtest Report ({window_size}d window)',
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
    )



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


def display_lvar(lvar_result, NAV):
    kpi = pd.DataFrame([
        ('VaR (1d 99%)',   f'{lvar_result["var"]*100:.2f}%',
         f'{lvar_result["var"]*NAV:,.0f}'),
        ('Liquidity cost', f'{lvar_result["liquidity_cost"]*100:.2f}%',
         f'{lvar_result["liquidity_cost"]*NAV:,.0f}'),
        ('LVaR (1d 99%)',  f'{lvar_result["lvar"]*100:.2f}%',
         f'{lvar_result["lvar"]*NAV:,.0f}'),
        ('LVaR increase',  f'+{lvar_result["lvar_pct_increase"]:.1f}%', ''),
    ], columns=['Metric', '% NAV', 'EUR'])
    display_dark_table(
        kpi,
        caption='Liquidity-Adjusted VaR',
        col_align_override={'% NAV': 'right', 'EUR': 'right'},
        col_widths={'Metric': '200px'},
    )
    bac = lvar_result['by_asset_class']
    display_dark_table(
        bac,
        caption='LVaR by Asset Class',
        fmt={'market_value_eur': '{:,.0f}', 'liquidity_cost': '{:,.0f}'},
    )


def display_granular(granular, NAV):
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
    display_dark_table(
        lot, caption='Leverage by Listed / OTC',
        fmt={'gross_eur': '{:,.0f}', _xnav(): '{:.2f}×', 'pct_leverage': '{:.1f}%'},
        highlight_rows=[len(lot) - 1],
    )

    # by source
    src = granular.groupby('source')['gross_eur'].sum().reset_index()
    src.columns = ['Source', 'gross_eur']
    src[_xnav()]    = src['gross_eur'] / NAV
    src['pct_leverage'] = src['gross_eur'] / total_gross * 100
    src = pd.concat([src, pd.DataFrame([{
        'Source': 'Total', 'gross_eur': total_gross,
        _xnav(): total_gross / NAV, 'pct_leverage': 100.0,
    }])], ignore_index=True)
    display_dark_table(
        src, caption='Leverage by Source',
        fmt={'gross_eur': '{:,.0f}', _xnav(): '{:.2f}×', 'pct_leverage': '{:.1f}%'},
        highlight_rows=[len(src) - 1],
    )

    # granular detail
    detail = granular[['asset_class', 'sub_asset_class', 'source', 'listed_otc',
                        'gross_eur', 'gross_x_nav', 'n_positions']].copy()
    detail = detail.rename(columns={'gross_x_nav': _xnav('Gross')})
    display_dark_table(
        detail, caption='AIFMD II Granular Leverage Breakdown',
        fmt={'gross_eur': '{:,.0f}', _xnav('Gross'): '{:.2f}×', 'n_positions': '{:.0f}'},
    )


def display_buckets(bucket_full, risk_df_liq, NAV):
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
    display_dark_table(
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
    )


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


def display_redemption_stress(fund_id, notice, redstress, NAV):
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
    display_dark_table(
        df,
        caption=f'Redemption Stress — {fund_id}  |  NAV: EUR {NAV:,.0f}  |  Notice: {notice}d',
        fmt={'redemption_eur': '{:,.0f}', 'liquid_eur': '{:,.0f}', 'coverage': '{:.2f}x'},
        col_styles={'coverage': lambda v: C['green'] if isinstance(v, float) and v >= 1.0 else C['red']},
    )


def display_counterparty_stress(NAV, _cp_hf, _worst_cp, _cp_loss_eur, _cp_loss_pct):
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

    display_dark_table(
        cp.drop(columns=['loss_pct_nav_raw']),
        caption=f'Counterparty Register — NAV: EUR {NAV:,.0f}',
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
    )


def display_combined_stress_mkt_plus_liq(NAV, _comb_mkt_eur, _comb_nav_st,
                                         _comb_redeem_eur, _comb_liquid_st,
                                         _comb_gap_st, _comb_action, _comb_cov_st):
    _total_stress = _comb_mkt_eur - max(0.0, -_comb_gap_st)
    _total_pct    = _total_stress / NAV * 100

    rows        = []
    sep_indices = []

    sep_indices.append(len(rows))
    rows.append(('MARKET SHOCK  —  EQUITY −20%', ''))
    rows.append(('  Portfolio P&L',  f"EUR {_comb_mkt_eur/1e6:,.1f}M   ({_comb_mkt_eur/NAV*100:.1f}% NAV)"))
    rows.append(('  Stressed NAV',   f"EUR {_comb_nav_st/1e6:,.1f}M"))

    sep_indices.append(len(rows))
    rows.append(('LIQUIDITY IMPACT  —  25% REDEMPTION, LIQUID ASSETS −20%', ''))
    rows.append(('  Redemption',    f"EUR {_comb_redeem_eur/1e6:,.1f}M   (25% pre-stress NAV)"))
    rows.append(('  Liquid assets', f"EUR {_comb_liquid_st/1e6:,.1f}M   (post equity shock)"))
    rows.append(('  Liquidity gap', f"EUR {_comb_gap_st/1e6:,.1f}M   |   Coverage: {_comb_cov_st:.2f}×"))
    rows.append(('  Action',        _comb_action))

    sep_indices.append(len(rows))
    rows.append(('TOTAL COMBINED IMPACT', ''))
    rows.append(('  Impact on NAV', f"EUR {_total_stress/1e6:,.1f}M   ({_total_pct:.1f}% of NAV)"))
    rows.append(('  Regulatory note', 'ESMA/2020/1498 §48 — combined stress is a mandatory Annex VI scenario'))

    df = pd.DataFrame(rows, columns=['Metric', 'Value'])
    display_dark_table(
        df,
        caption=f'Combined Stress — Equity −20% + 25% Redemption  |  Baseline NAV: EUR {NAV/1e6:,.1f}M',
        highlight_rows=sep_indices,
        col_styles={'Value': lambda v: (
            C['red']   if isinstance(v, str) and v.startswith('EUR') and '-' in v else
            C['red']   if isinstance(v, str) and v.startswith('-') else
            C['amber'] if isinstance(v, str) and 'ESMA' in v else None
        )},
        col_align_override={'Value': 'right'},
        col_widths={'Metric': '240px', 'Value': '260px'},
    )


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


def display_historical_scenarios(historical_scenarios: dict):
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
    display_dark_table(
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
    )


def display_scenarios(risk_df, custom: dict | None = None, add_historical: bool = False):
    """Render stress scenario P&L results — custom and/or historical."""
    from src.risk_utils import HISTORICAL_SCENARIOS, stress_historical
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

    display_dark_table(
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
    )


def display_ptc(result: dict, test_number: int | None = None) -> None:
    """Render a pre-trade check result as a hand-built HTML table with colspan."""
    t        = result['proposed_trade']
    notional = abs(t['quantity'] * t['price_eur'])
    status   = '✓  PASSED' if result['passed'] else '✗  FAILED'
    pre      = result.get('pre_trade_metrics', {})
    cap_txt  = (f'Pre-Trade Evaluation #{test_number}'
                if test_number is not None else 'Pre-Trade Evaluation')

    def _fmt(k: str, v) -> str:
        if not isinstance(v, float): return str(v)
        k = k.lower()
        if any(x in k for x in ('leverage', 'multiplier')): return f'{v:.2f}×'
        if any(x in k for x in ('exposure', 'bonds', 'net_eq', 'borrowing',
                                 'fx_exposure', 'notional', 'deriv_')): return f'{v:,.0f}'
        if 'pct' in k or 'var' in k: return f'{v:.2f}%'
        if v > 10_000: return f'{v:,.0f}'
        return f'{v:.2f}'

    # — shared styles ——————————————————————————————————————————————
    _BG_E   = '#1a1f2e'
    _BG_O   = '#141929'
    _BG_SEP = '#36394F'
    _BG_HDR = '#2F3245'
    _TXT    = '#9ca3af'
    _HDR_C  = '#a5cfdf'
    _SEP_C  = '#587580'
    _BORDER = '1px solid #0f1729'
    _FONT   = 'font-family:Arial,sans-serif;font-size:11px;'
    _PAD    = 'padding:5px 12px;'

    def _sep(label, colspan=3):
        return (f'<tr style="background:{_BG_SEP};">'
                f'<td colspan="{colspan}" style="{_FONT}{_PAD}color:{_SEP_C};'
                f'font-weight:bold;letter-spacing:0.05em;text-transform:uppercase;'
                f'text-align:left;border-bottom:{_BORDER};">{label}</td></tr>')

    def _spacer(n, colspan=3):
        bg = _BG_E if n % 2 == 0 else _BG_O
        return f'<tr style="background:{bg};"><td colspan="{colspan}" style="padding:3px;border-bottom:{_BORDER};"></td></tr>'

    def _detail(label, value, n, val_color=None, label_color=None):
        bg   = _BG_E if n % 2 == 0 else _BG_O
        lc   = label_color or _TXT
        vc   = val_color   or _TXT
        return (f'<tr style="background:{bg};">'
                f'<td style="{_FONT}{_PAD}color:{lc};text-align:left;border-bottom:{_BORDER};">{label}</td>'
                f'<td colspan="2" style="{_FONT}{_PAD}color:{vc};text-align:left;border-bottom:{_BORDER};">{value}</td>'
                '</tr>')

    def _metric(label, pre_v, post_v, n):
        bg  = _BG_E if n % 2 == 0 else _BG_O
        pc  = C['green'] if '✓' in post_v or (post_v and '⚠' not in post_v and '✗' not in post_v) else _TXT
        psc = C['red'] if '⚠' in post_v or '✗' in post_v else _TXT
        return (f'<tr style="background:{bg};">'
                f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:left;border-bottom:{_BORDER};">{label}</td>'
                f'<td style="{_FONT}{_PAD}color:{_TXT};text-align:right;border-bottom:{_BORDER};">{pre_v}</td>'
                f'<td style="{_FONT}{_PAD}color:{psc};text-align:right;border-bottom:{_BORDER};">{post_v}</td>'
                '</tr>')

    rows_html = []
    n = 0

    # — colgroup — defines the 3-column layout
    colgroup = '<colgroup><col style="width:220px;"><col style="width:120px;"><col style="width:150px;"></colgroup>'

    # — caption & thead ——————————————————————————————————————————
    caption_html = (
        f'<caption style="color:{C["cyan"]};font-size:14px;font-weight:bold;'
        f'text-align:left;font-family:Helvetica Neue,Arial,sans-serif;'
        f'padding-bottom:8px;background:#1a2540;">{cap_txt}</caption>'
    )
    # no column headers — table structure is self-describing via separators

    # — trade details (no pre/post header here) ———————————————————
    rows_html.append(_sep('FUND AND POTENTIAL TRADE DETAILS'))
    for label, val in [
        ('Fund',     result['fund_id']),
        ('Trade',    f"{t['direction'].upper()}  {t['quantity']:,} × {t['isin']}"),
        ('Notional', f"EUR {notional:,.0f}   @   EUR {t['price_eur']:,.2f}"),
        ('Result',   status),
    ]:
        vc = C['green'] if '✓' in val else C['red'] if '✗' in val else _TXT
        rows_html.append(_detail(f'&nbsp;&nbsp;{label}', val, n, val_color=vc)); n += 1

    # — metrics (pre vs post) ————————————————————————————————————
    rows_html.append(_spacer(n)); n += 1
    # separator doubles as column header for this section
    rows_html.append(
        f'<tr style="background:{_BG_SEP};">'
        f'<td style="{_FONT}{_PAD}color:{_SEP_C};font-weight:bold;letter-spacing:0.05em;'
        f'text-transform:uppercase;text-align:left;border-bottom:{_BORDER};">METRICS</td>'
        f'<td style="{_FONT}{_PAD}color:{_SEP_C};font-weight:bold;letter-spacing:0.05em;'
        f'text-transform:uppercase;text-align:right;border-bottom:{_BORDER};">PRE-TRADE</td>'
        f'<td style="{_FONT}{_PAD}color:{_SEP_C};font-weight:bold;letter-spacing:0.05em;'
        f'text-transform:uppercase;text-align:right;border-bottom:{_BORDER};">POST-TRADE</td>'
        '</tr>'
    )
    for k, v in result['post_trade_metrics'].items():
        rows_html.append(_metric(f'&nbsp;&nbsp;{k}', _fmt(k, pre[k]) if k in pre else '', _fmt(k, v), n))
        n += 1

    # — breaches —————————————————————————————————————————————————
    rows_html.append(_spacer(n)); n += 1
    if result['breaches']:
        rows_html.append(_sep(f"BREACHES DETECTED  ({len(result['breaches'])})"))
        for b in result['breaches']:
            rows_html.append(_spacer(n)); n += 1
            rows_html.append(_detail(f'&nbsp;&nbsp;⚠&nbsp;{b["check"]}', '', n, label_color=C['red'])); n += 1
            rows_html.append(_detail('&nbsp;&nbsp;&nbsp;&nbsp;Limit',  f"{b['limit']} {b['unit']}",  n)); n += 1
            rows_html.append(_detail('&nbsp;&nbsp;&nbsp;&nbsp;Actual', f"{b['actual']} {b['unit']}", n)); n += 1
            rows_html.append(_detail('&nbsp;&nbsp;&nbsp;&nbsp;Detail', b['message'],                 n)); n += 1
    else:
        rows_html.append(_sep('NO LIMIT BREACHES — TRADE APPROVED', colspan=3))

    table = (
        f'<table style="border-collapse:collapse;width:100%;background:{_BG_E};">'
        f'{caption_html}{colgroup}<tbody>{"".join(rows_html)}</tbody></table>'
    )
