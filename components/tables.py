"""Reusable table components for the analytics dashboard."""

from dash import html
import numpy as np


def heatmap_color(val, vmin, vmax):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 'rgb(240,240,240)'
    if val == 0:
        return 'rgb(255,255,255)'
    if val > 0:
        intensity = min(abs(val) / 3.0, 1.0)
        r = int(255 - intensity * 180)
        g = 255
        b = int(255 - intensity * 180)
        return f'rgb({r},{g},{b})'
    else:
        intensity = min(abs(val) / 3.0, 1.0)
        r = 255
        g = int(255 - intensity * 180)
        b = int(255 - intensity * 180)
        return f'rgb({r},{g},{b})'


def build_returns_table(table_df, since_label, sort_state, selected_funds=None, clickable=False, header_type='holdings'):
    return_cols = ['1D', '1W', '1M', '3M', 'YTD', 'Since']
    selected_funds = selected_funds or []
    
    col_ranges = {}
    for col in return_cols:
        vals = table_df[col].dropna()
        col_ranges[col] = (vals.min(), vals.max()) if len(vals) > 0 else (0, 0)
    
    col_defs = [
        ('Fund',       'Fund',  False, 'left'),
        ('Type',       'Type',  False, 'center'),
        ('Price',      'Price', False, 'right'),
        ('1D %',       '1D',    True,  'right'),
        ('1W %',       '1W',    True,  'right'),
        ('1M %',       '1M',    True,  'right'),
        ('3M %',       '3M',    True,  'right'),
        ('YTD %',      'YTD',   True,  'right'),
        (since_label,  'Since', True,  'right'),
    ]
    
    def sort_arrow(col_key):
        if sort_state['col'] == col_key:
            return ' ▲' if sort_state['asc'] else ' ▼'
        return ' ⇅'
    
    header = html.Thead(html.Tr([
        html.Th(
            f"{label}{sort_arrow(key)}",
            id={'type': f'sort-header-{header_type}', 'col': key},
            n_clicks=0,
            style={
                'backgroundColor': '#1a3a5c', 'color': 'white',
                'padding': '4px 6px', 'fontSize': '10px', 'fontWeight': '600',
                'textAlign': align, 'whiteSpace': 'nowrap',
                'cursor': 'pointer', 'userSelect': 'none',
            }
        ) for label, key, _, align in col_defs
    ]))
    
    rows = []
    for _, row in table_df.iterrows():
        fid = row['fund_id']
        is_selected = fid in selected_funds
        row_bg = '#e8f0f8' if is_selected else 'transparent'
        
        max_len = 28
        fund_name = str(row['Fund']) if row['Fund'] and str(row['Fund']) != 'nan' else row['fund_id']
        fund_disp = fund_name if len(fund_name) <= max_len else fund_name[:max_len-1] + '…'
        
        cells = [
            html.Td(
                html.Div([
                    html.Span('● ' if is_selected else '', style={
                        'color': '#2E75B6', 'fontSize': '8px',
                        'marginRight': '3px', 'width': '8px', 'display': 'inline-block',
                    }),
                    html.Span(fund_disp, title=fund_name),
                ]),
                style={
                    'padding': '3px 6px', 'fontSize': '11px',
                    'fontWeight': '600' if is_selected else '400',
                    'color': '#1a3a5c', 'whiteSpace': 'nowrap',
                    'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis',
                }
            ),
            html.Td(
                html.Span(row['Type'], style={
                    'fontSize': '8px', 'padding': '1px 4px', 'borderRadius': '3px',
                    'fontWeight': '500', 'backgroundColor': _type_badge_color(row['Type']),
                    'color': '#555',
                }),
                style={'padding': '3px 4px', 'textAlign': 'center'}
            ),
            html.Td(
                f"{row['Price']:.1f}" if row['Price'] and str(row['Price']) != 'nan' and row['Price'] != 'N/A' else '—',
                style={
                    'padding': '3px 6px', 'fontSize': '11px',
                    'textAlign': 'right', 'fontFamily': 'monospace', 'color': '#444',
                }
            ),
        ]
        
        for col in return_cols:
            val = row[col]
            vmin, vmax = col_ranges[col]
            bg = heatmap_color(val, vmin, vmax)
            if val is not None and not np.isnan(val):
                formatted = f"{val:+.1f}%"
            else:
                formatted = '—'
                bg = 'rgb(248,248,248)'
            
            cells.append(html.Td(formatted, style={
                'padding': '3px 5px', 'fontSize': '10px',
                'textAlign': 'right', 'fontWeight': '600',
                'fontFamily': 'monospace', 'backgroundColor': bg,
                'color': '#1a1a1a', 'borderRadius': '2px',
            }))
        
        tr_style = {'borderBottom': '1px solid #f0f3f7', 'backgroundColor': row_bg}
        if clickable:
            tr_style['cursor'] = 'pointer'
            tr = html.Tr(cells, id={'type': f'{header_type}-row', 'fund_id': fid}, n_clicks=0, style=tr_style)
        else:
            tr = html.Tr(cells, style=tr_style)
        
        rows.append(tr)
    
    return html.Table(
        [header, html.Tbody(rows)],
        style={'width': '100%', 'borderCollapse': 'collapse'},
    )


def _type_badge_color(asset_type):
    colors = {
        'Fund': '#e8f0f8', 'ETF': '#e8f5e9', 'Stock': '#fff3e0',
        'Index': '#f3e5f5', 'Commodity': '#fff8e1', 'Crypto': '#ffebee',
        'Cash': '#f5f5f5', 'Bond': '#e0f2f1',
    }
    return colors.get(asset_type, '#f5f5f5')