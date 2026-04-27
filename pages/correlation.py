"""Correlation Matrix page for portfolio analytics."""

import dash
from dash import html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from data.queries import load_prices, load_portfolio_holdings, load_instruments
from calculations.correlation import (
    build_return_series,
    correlation_matrix,
    cluster_ordering,
    top_overlap_pairs
)

dash.register_page(__name__, path='/correlation', name='Correlation Matrix')


# ── Layout ─────────────────────────────────────────────────────

layout = html.Div([
    html.Div([
        html.H2("Correlation Matrix", style={
            'color': '#1a3a5c', 'fontSize': '18px',
            'fontWeight': '700', 'marginBottom': '4px'
        }),
        html.P(
            "How your holdings move together. Red = together, Blue = opposite, White = unrelated.",
            style={'color': '#888', 'fontSize': '12px', 'marginTop': '0'}
        ),
    ], style={'marginBottom': '16px'}),
    
    # Controls row 1: Lookback, method, cluster toggle
    html.Div([
        html.Div([
            html.Label("Lookback:", style={
                'fontSize': '11px', 'color': '#666', 'marginRight': '6px'
            }),
            dcc.Dropdown(
                id='corr-lookback',
                options=[
                    {'label': '1 Month', 'value': '1M'},
                    {'label': '3 Months', 'value': '3M'},
                    {'label': '6 Months', 'value': '6M'},
                    {'label': '1 Year', 'value': '1Y'},
                    {'label': 'All Data', 'value': 'ALL'},
                ],
                value='1Y',
                clearable=False,
                style={'width': '130px', 'fontSize': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
        
        html.Div([
            html.Label("Method:", style={
                'fontSize': '11px', 'color': '#666', 'marginRight': '6px'
            }),
            dcc.Dropdown(
                id='corr-method',
                options=[
                    {'label': 'Pearson', 'value': 'pearson'},
                    {'label': 'Spearman', 'value': 'spearman'},
                ],
                value='pearson',
                clearable=False,
                style={'width': '120px', 'fontSize': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
        
        html.Div([
            html.Label("Cluster:", style={
                'fontSize': '11px', 'color': '#666', 'marginRight': '6px'
            }),
            dcc.Checklist(
                id='corr-cluster-toggle',
                options=[{'label': 'Group by similarity', 'value': 'cluster'}],
                value=['cluster'],
                style={'fontSize': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center'}),
    ], style={
        'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap',
        'marginBottom': '10px', 'padding': '10px 16px',
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'boxShadow': '0 1px 4px rgba(0,0,0,0.08)'
    }),
    
    # Controls row 2: Instrument selector (NEW)
    html.Div([
        html.Label("Instruments:", style={
            'fontSize': '11px', 'color': '#666', 'marginRight': '8px',
            'alignSelf': 'flex-start', 'marginTop': '6px'
        }),
        html.Div([
            dcc.Dropdown(
                id='corr-instrument-selector',
                options=[],  # populated by callback
                value=[],    # populated by callback
                multi=True,
                placeholder="Select instruments to include (default: your holdings)...",
                style={'fontSize': '12px'},
            ),
            html.Div([
                html.Button("Load Holdings", id='corr-load-holdings-btn', n_clicks=0, style={
                    'backgroundColor': '#2E75B6', 'color': 'white', 'border': 'none',
                    'borderRadius': '4px', 'padding': '6px 12px', 'fontSize': '11px',
                    'cursor': 'pointer', 'marginRight': '6px',
                }),
                html.Button("Clear All", id='corr-clear-btn', n_clicks=0, style={
                    'backgroundColor': '#999', 'color': 'white', 'border': 'none',
                    'borderRadius': '4px', 'padding': '6px 12px', 'fontSize': '11px',
                    'cursor': 'pointer',
                }),
            ], style={'display': 'flex', 'gap': '6px', 'marginTop': '6px'}),
        ], style={'flex': '1'}),
    ], style={
        'display': 'flex', 'alignItems': 'flex-start',
        'marginBottom': '16px', 'padding': '10px 16px',
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'boxShadow': '0 1px 4px rgba(0,0,0,0.08)'
    }),
    
    # Correlation heatmap
    html.Div([
        dcc.Graph(
            id='correlation-heatmap',
            config={'displayModeBar': True, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']},
            style={'height': '650px'}
        ),
    ], style={
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'padding': '12px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
        'marginBottom': '16px'
    }),
    
    # Overlap pairs table
    html.Div([
        html.H3("Top Overlapping Pairs", style={
            'color': '#1a3a5c', 'fontSize': '14px',
            'fontWeight': '600', 'marginBottom': '8px'
        }),
        html.Div(id='corr-overlap-table'),
    ], style={
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'padding': '14px 18px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
    }),
    
    # Stores
    dcc.Store(id='corr-matrix-store'),
    dcc.Store(id='corr-ordered-funds-store'),
])


# ── Callback: Populate instrument dropdown ─────────────────────

@callback(
    Output('corr-instrument-selector', 'options'),
    Output('corr-instrument-selector', 'value'),
    Input('corr-load-holdings-btn', 'n_clicks'),
    Input('corr-clear-btn', 'n_clicks'),
)
def populate_instruments(load_clicks, clear_clicks):
    """Load all instruments from database and set defaults."""
    instruments_df = load_instruments()
    holdings_df = load_portfolio_holdings()
    
    # Build options list grouped by category
    options = []
    for cat, group in instruments_df.groupby('category', dropna=False):
        cat_label = cat if cat else 'Uncategorised'
        cat_options = [
            {'label': f"{row['name']} ({cat_label})", 'value': row['fund_id']}
            for _, row in group.iterrows()
        ]
        options.append({'label': f"── {cat_label} ──", 'value': f'_header_{cat_label}', 'disabled': True})
        options.extend(cat_options)
    
    # Determine default selection
    ctx = dash.callback_context
    triggered = ctx.triggered_id
    
    if triggered == 'corr-clear-btn':
        default_value = []
    else:
        # Default: all current holdings
        default_value = holdings_df['fund_id'].tolist() if not holdings_df.empty else []
    
    return options, default_value


# ── Main Callback: Update heatmap and overlap table ────────────

@callback(
    Output('correlation-heatmap', 'figure'),
    Output('corr-overlap-table', 'children'),
    Output('corr-matrix-store', 'data'),
    Output('corr-ordered-funds-store', 'data'),
    Input('corr-lookback', 'value'),
    Input('corr-method', 'value'),
    Input('corr-cluster-toggle', 'value'),
    Input('corr-instrument-selector', 'value'),
)
def update_correlation(lookback, method, cluster_toggle, selected_ids):
    # ── 1. Validate inputs ───────────────────────────────────
    if not selected_ids:
        return empty_figure("No instruments selected. Use the dropdown above to add funds."), "", None, None
    
    # ── 2. Load data ─────────────────────────────────────────
    min_date = None
    if lookback != 'ALL':
        days_map = {'1M': 21, '3M': 63, '6M': 126, '1Y': 252}
        cutoff = pd.Timestamp.today() - pd.Timedelta(days=days_map.get(lookback, 126))
        min_date = cutoff.strftime('%Y-%m-%d')
    
    prices_df = load_prices(fund_ids=selected_ids, min_date=min_date)
    
    if prices_df.empty:
        return empty_figure("No price data available for selected instruments."), "", None, None
    
    # ── 3. Build returns and correlation matrix ──────────────
    returns_df = build_return_series(prices_df, min_days=10)
    
    if returns_df.empty or returns_df.shape[1] < 2:
        return empty_figure("Need at least 2 instruments with sufficient data. Try a longer lookback."), "", None, None
    
    corr_matrix = correlation_matrix(returns_df, method=method, min_overlap=20)
    
    if corr_matrix.empty:
        return empty_figure("Not enough overlapping data to calculate correlations."), "", None, None
    
    # ── 4. Get readable labels ───────────────────────────────
    instruments_df = load_instruments(fund_ids=corr_matrix.columns.tolist())
    name_map = dict(zip(instruments_df['fund_id'], instruments_df['name']))
    cat_map = dict(zip(instruments_df['fund_id'], instruments_df['category']))
    
    def make_label(fid):
        name = name_map.get(fid, fid)
        cat = cat_map.get(fid, '')
        short_name = name if len(name) <= 28 else name[:26] + '…'
        return f"{short_name} ({cat})" if cat else short_name
    
    labels = {fid: make_label(fid) for fid in corr_matrix.columns}
    
    # ── 5. Cluster ordering (optional) ───────────────────────
    do_cluster = 'cluster' in (cluster_toggle or [])
    
    if do_cluster and len(corr_matrix.columns) > 2:
        ordered = cluster_ordering(corr_matrix)
    else:
        ordered = corr_matrix.columns.tolist()
    
    corr_matrix = corr_matrix.loc[ordered, ordered]
    ordered_labels = [labels[fid] for fid in ordered]
    
    # ── 6. Build heatmap ────────────────────────────────────
    z = corr_matrix.values
    z_text = [[f"{v:.3f}" if not np.isnan(v) else "N/A" for v in row] for row in z]
    
    colorscale = [
        [0.0, '#2166ac'],
        [0.25, '#67a9cf'],
        [0.5, '#f7f7f7'],
        [0.75, '#ef8a62'],
        [1.0, '#b2182b'],
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=ordered_labels,
        y=ordered_labels,
        zmin=-1, zmax=1,
        colorscale=colorscale,
        text=z_text,
        texttemplate='%{text}',
        textfont={'size': 9},
        hoverongaps=False,
        hovertemplate='%{x}<br>⇄ %{y}<br><b>%{z:.3f}</b><extra></extra>',
        showscale=True,
        colorbar=dict(
            title=dict(text='Correlation', side='right'),
            thickness=15,
            len=0.6,
        ),
    ))
    
    fig.update_layout(
        xaxis={'side': 'bottom', 'tickangle': -45, 'tickfont': {'size': 9}},
        yaxis={'tickfont': {'size': 9}},
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=10, r=30, t=10, b=120),
        height=max(450, 80 + len(ordered) * 22),
    )
    
    # ── 7. Overlap pairs table ───────────────────────────────
    pairs_df = top_overlap_pairs(corr_matrix, min_correlation=0.7)
    
    if pairs_df.empty:
        overlap_table = html.P(
            "No pairs with correlation ≥ 0.7 found.",
            style={'color': '#888', 'fontSize': '12px'}
        )
    else:
        pairs_df['Name 1'] = pairs_df['fund_1'].map(lambda x: name_map.get(x, x))
        pairs_df['Name 2'] = pairs_df['fund_2'].map(lambda x: name_map.get(x, x))
        
        rows = []
        for _, row in pairs_df.iterrows():
            corr_val = row['correlation']
            if corr_val >= 0.9:
                bg = '#ffe0e0'
                color = '#b2182b'
            elif corr_val >= 0.8:
                bg = '#fff0e0'
                color = '#d6604d'
            else:
                bg = '#fffaf0'
                color = '#ef8a62'
            
            rows.append(html.Tr([
                html.Td(row['Name 1'], style={'padding': '6px 10px', 'fontSize': '12px', 'color': '#1a3a5c'}),
                html.Td(row['Name 2'], style={'padding': '6px 10px', 'fontSize': '12px', 'color': '#1a3a5c'}),
                html.Td(f"{corr_val:.3f}", style={
                    'padding': '6px 10px', 'fontSize': '12px', 'textAlign': 'center',
                    'fontFamily': 'monospace', 'fontWeight': '700',
                    'backgroundColor': bg, 'color': color, 'borderRadius': '4px',
                }),
            ]))
        
        overlap_table = html.Table(
            [html.Thead(html.Tr([
                html.Th("Holding 1", style=th_style),
                html.Th("Holding 2", style=th_style),
                html.Th("Correlation", style={**th_style, 'textAlign': 'center'}),
            ])),
            html.Tbody(rows),
        ], style={'width': '100%', 'borderCollapse': 'collapse'})
    
    store_data = {'fund_id': ordered, 'labels': ordered_labels}
    
    return fig, overlap_table, corr_matrix.to_json(), store_data


# ── Helpers ────────────────────────────────────────────────────

th_style = {
    'backgroundColor': '#1a3a5c', 'color': 'white',
    'padding': '6px 10px', 'fontSize': '11px', 'fontWeight': '600',
    'textAlign': 'left', 'whiteSpace': 'nowrap',
}


def empty_figure(message):
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5,
        xref='paper', yref='paper',
        showarrow=False,
        font=dict(size=14, color='#999')
    )
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=400, margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig