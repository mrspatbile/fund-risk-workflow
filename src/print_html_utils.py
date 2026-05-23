from IPython.display import display, HTML
import pandas as pd
from src.plot_style import C



def display_dark_table(
    df,
    caption             : str        = '',
    fmt                 : dict | None = None,
    col_styles          : dict | None = None,
    first_col_left      : bool = True,
    col_align_override  : dict | None = None,
    highlight_rows      : list | None = None,
):
    def _fmt_col(col):
        col = col.replace('_', ' ')
        if 'eur' in col.lower():
            col = col.replace(' eur', '').replace('eur ', '').strip()
            col = f'{col}\n(EUR)'
        return col.title()

    df_display          = df.rename(columns={c: _fmt_col(c) for c in df.columns})
    col_map             = dict(zip(df.columns, df_display.columns))
    col_styles_remapped = {col_map[k]: v for k, v in col_styles.items() if k in col_map} if col_styles else None
    fmt_remapped        = {col_map.get(k, k): v for k, v in fmt.items()} if fmt else None

    def _style(df):
        styles = []
        for i, row in df.iterrows():
            is_highlight   = highlight_rows and i in highlight_rows
            bg             = '#2F3245' if is_highlight else ('#1a1f2e' if i % 2 == 0 else '#141929')
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
            if df[col].dtype in ('float64', 'int64', 'bool'):
                aligns[col] = 'right'
            else:
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
            ('text-align',       'center'),
            ('padding',          '6px 12px'),
            ('border-bottom',    '2px solid #0f1729'),
            ('color',            '#a5cfdf'),
            ('letter-spacing',   '0.05em'),
            ('text-transform',   'uppercase'),
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

    styled = df_display.style.apply(_style, axis=None).set_table_styles(table_styles)

    if caption:
        styled = styled.set_caption(caption)
    if fmt_remapped:
        styled = styled.format(fmt_remapped, na_rep='—')

    styled = styled.hide(axis='index')
    display(styled)

