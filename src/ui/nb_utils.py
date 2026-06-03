"""
nb_utils.py
===========
Shared notebook utilities: figure saving and dark-themed table rendering.

Keeps notebooks clean by centralising the two most repeated patterns:
  - saving matplotlib figures to a per-fund report directory
  - rendering DataFrames as dark-themed HTML tables consistent with the
    covenant monitor style defined in aifm_infra_fund.ipynb

Usage
-----
    from src.ui.nb_utils import save_fig, styled_table
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
from IPython.display import HTML, display

from src.ui.plot_style import C
import dataframe_image as dfi

import asyncio
import nest_asyncio
from playwright.async_api import async_playwright


# ── Figure saving ──────────────────────────────────────────────────────────────
def _make_output_path(fund_id: str, filename: str, ext: str = 'png') -> Path:
    out_dir = Path('reports') / fund_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f'{filename}.{ext}'

def save_fig(fig, fund_id: str, filename: str, dpi: int = 150) -> str:
    """
    Save a matplotlib figure to reports/<fund_id>/<filename>.png.

    Creates the directory tree if it does not exist. Uses the figure's
    own facecolor so the dark background is preserved in the PNG.

    Parameters
    ----------
    fig      : matplotlib Figure
    fund_id  : str  — used as the sub-directory name, e.g. 'AIFM_HedgeFund'
    filename : str  — base filename without extension
    dpi      : int  — output resolution (default 150)

    Returns
    -------
    str : absolute path of the saved file
    """
    path = _make_output_path(fund_id, filename)
    fig.savefig(path, dpi=dpi, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    return str(path)



def save_table(styled_df, fund_id: str, filename: str, dpi: int = 150, table_conversion='matplotlib') -> str:
    """
    Save a styled dataframe to reports/<fund_id>/<filename>.png.

    Creates the directory tree if it does not exist.

    Parameters
    ----------
    styled_df : pandas Styler
    fund_id   : str  — used as the sub-directory name, e.g. 'AIFM_HedgeFund'
    filename  : str  — base filename without extension
    dpi       : int  — output resolution (default 150)

    Returns
    -------
    str : absolute path of the saved file
    """
    path = _make_output_path(fund_id, filename)
    dfi.export(styled_df, str(path), dpi=dpi, table_conversion='matplotlib')
    return str(path)


def save_table_html(html, fund_id, filename):
    path = _make_output_path(fund_id, filename, ext='html')
    with open(path, 'w') as f:
        f.write(html)
    return str(path)



nest_asyncio.apply()

async def _save_table_png_async(html: str, path: str) -> None:
    full_html = f"""
    <html>
    <body style="background:#0d1b2a; margin:0; padding:16px;">
    {html}
    </body>
    </html>
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(full_html)
        await page.locator('table').screenshot(path=path)
        await browser.close()


def save_table_png(html: str, fund_id: str, filename: str) -> str:
    path = _make_output_path(fund_id, filename, ext='png')
    asyncio.get_event_loop().run_until_complete(
        _save_table_png_async(html, str(path))
    )
    return str(path)


# ── Dark-themed HTML table ─────────────────────────────────────────────────────

_TABLE_CSS = """
<style>
  table.nb  {{ border-collapse: collapse; font-size: {font_size}px; width: 100%; }}
  table.nb th {{ background-color: {header_bg}; color: {header_fg}; padding: 6px 12px;
                  text-align: center; border-bottom: 1px solid {border}; }}
  table.nb td {{ padding: 5px 12px; text-align: {col_align};
                  border-bottom: 1px solid {row_border}; color: white; }}
</style>
"""


def styled_table(
    df: pd.DataFrame,
    title: str = '',
    row_color_fn: Callable[[dict], str] | None = None,
    col_align: str = 'center',
    font_size: int = 11,
) -> None:
    """
    Display a DataFrame as a dark-themed HTML table.

    Matches the visual style of the covenant monitor (table.cov) used in the
    infrastructure notebook: dark header, dark rows, white text, subtle
    row separators.

    Parameters
    ----------
    df           : DataFrame to render
    title        : optional heading rendered above the table in white
    row_color_fn : optional callable(row_dict) -> CSS hex color string
                   Controls the background of each data row. Return value is
                   used as the CSS background-color of the <tr>. Defaults to
                   C['bg3'] (#1a1f2e) for all rows.
    col_align    : CSS text-align for data cells ('center', 'left', 'right')
    font_size    : font size in pixels for both header and data cells
    """
    css = _TABLE_CSS.format(
        font_size  = font_size,
        header_bg  = C['bg'],
        header_fg  = C['text'],
        border     = C['border'],
        row_border = C['bg4'],
        col_align  = col_align,
    )

    header = ''.join(f'<th>{col}</th>' for col in df.columns)

    rows_html = ''
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        bg = row_color_fn(row_dict) if row_color_fn else C['bg3']
        cells = ''.join(f'<td>{v}</td>' for v in row_dict.values())
        rows_html += f'<tr style="background-color:{bg};">{cells}</tr>'

    table = (
        f'{css}'
        f'<table class="nb">'
        f'  <thead><tr>{header}</tr></thead>'
        f'  <tbody>{rows_html}</tbody>'
        f'</table>'
    )

    heading = (
        f'<p style="color:{C["text"]};font-weight:bold;'
        f'font-size:{font_size + 1}px;margin-bottom:4px;">{title}</p>'
        if title else ''
    )

    display(HTML(heading + table))
