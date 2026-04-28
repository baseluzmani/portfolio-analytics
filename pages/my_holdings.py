"""My Holdings page — personalised view of portfolio performance."""

import dash
from dash import html, dcc, Input, Output, State, callback, ctx, ALL
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from data.queries import load_prices, load_portfolio_holdings, load_instruments
from calculations.returns import build_returns_table, calc_return
from components.tables import build_returns_table as render_table

dash.register_page(__name__, path='/my-holdings', name='My Holdings')


def layout():
    holdings_df = load_portfolio_holdings()
    holding_ids = holdings_df['fund_id'].tolist() if not holdings_df.empty else []
    
    prices_df = load_prices(fund_ids=holding_ids)
    max_date = prices_df['date'].max().date() if not prices_df.empty else datetime.today().date()
    min_date = prices_df['date'].min().date() if not prices_df.empty else datetime.today().date()
    
    default_since = '2026-03-01'
    
    return html.Div([
        html.Div([
            html.Div([
                html.H2("My Holdings", style={
                    'color': '#1a3a5c', 'fontSize': '18px',
                    'fontWeight': '700', 'marginBottom': '4px'
                }),
                html.P(
                    "Your portfolio holdings. Click rows to select for the chart.",
                    style={'color': '#888', 'fontSize': '12px', 'marginTop': '0'}
                ),
            ]),
            html.Div([
                html.Label("Since:", style={
                    'fontSize': '11px', 'color': '#666', 'marginRight': '8px'
                }),
                dcc.DatePickerSingle(
                    id='holdings-since-date',
                    date=default_since,
                    min_date_allowed=min_date,
                    max_date_allowed=max_date,
                    display_format='DD MMM YYYY',
                ),
            ], style={'display': 'flex', 'alignItems': 'center'}),
        ], style={
            'display': 'flex', 'justifyContent': 'space-between',
            'alignItems': 'flex-start', 'marginBottom': '16px'
        }),
        
        html.Div([
            html.Div([
                html.Div(id='holdings-table-container'),
            ], style={
                'flex': '1', 'minWidth': '0', 'overflow': 'hidden',
                'backgroundColor': '#fff', 'borderRadius': '8px',
                'padding': '10px 14px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
                'marginRight': '12px',
            }),
            
            html.Div([
                html.Div([
                    html.P("RELATIVE RETURNS", style={
                        'color': '#1a3a5c', 'fontSize': '11px',
                        'fontWeight': '700', 'letterSpacing': '0.08em',
                        'textTransform': 'uppercase', 'marginBottom': '4px',
                    }),
                    html.Span(id='holdings-chart-info', style={'fontSize': '11px', 'color': '#aaa'}),
                ], style={'marginBottom': '8px'}),
                dcc.Graph(
                    id='holdings-relative-chart',
                    config={'displayModeBar': False},
                    style={'height': '420px'}
                ),
            ], style={
                'flexShrink': '0', 'width': '380px',
                'backgroundColor': '#fff', 'borderRadius': '8px',
                'padding': '14px 18px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
            }),
        ], style={'display': 'flex', 'alignItems': 'flex-start', 'width': '100%'}),
        
        dcc.Store(id='holdings-selected-funds', data=[]),
        dcc.Store(id='holdings-sort-state', data={'col': 'YTD', 'asc': False}),
        dcc.Interval(id='holdings-auto-refresh', interval=60*60*1000, n_intervals=0),
    ])


@callback(
    Output('holdings-selected-funds', 'data', allow_duplicate=True),
    Input({'type': 'holdings-row', 'fund_id': ALL}, 'n_clicks'),
    State('holdings-selected-funds', 'data'),
    prevent_initial_call=True,
)
def toggle_holding(n_clicks, selected):
    if not any(n_clicks):
        return selected
    triggered = ctx.triggered_id
    if not triggered:
        return selected
    fid = triggered['fund_id']
    selected = list(selected or [])
    if fid in selected:
        selected.remove(fid)
    else:
        selected.append(fid)
    return selected


@callback(
    Output('holdings-table-container', 'children'),
    Output('holdings-sort-state', 'data'),
    Input('holdings-since-date', 'date'),
    Input({'type': 'sort-header-holdings', 'col': ALL}, 'n_clicks'),
    Input('holdings-selected-funds', 'data'),
    State('holdings-sort-state', 'data'),
)
def update_holdings(since_date, n_clicks, selected_funds, sort_state):
    since_date = since_date or '2026-03-01'
    selected_funds = selected_funds or []
    
    triggered = ctx.triggered_id
    if triggered and isinstance(triggered, dict) and triggered.get('type') == 'sort-header-holdings':
        clicked_col = triggered['col']
        if sort_state['col'] == clicked_col:
            sort_state['asc'] = not sort_state['asc']
        else:
            sort_state['col'] = clicked_col
            sort_state['asc'] = False
    
    portfolio = load_portfolio_holdings()
    if portfolio.empty:
        return html.P("No holdings found.", style={'color': '#999', 'fontSize': '12px'}), sort_state
    
    holding_ids = portfolio['fund_id'].tolist()
    prices_df = load_prices(fund_ids=holding_ids)
    
    if prices_df.empty:
        return html.P("No price data available.", style={'color': '#999'}), sort_state
    
    instruments_df = load_instruments(fund_ids=holding_ids)
    name_map = dict(zip(instruments_df['fund_id'], instruments_df['name']))
    
    table_df = build_returns_table(prices_df, since_date)
    table_df['Fund'] = table_df['fund_id'].map(lambda fid: name_map.get(fid, fid))
    
    sort_col = sort_state['col']
    sort_asc = sort_state['asc']
    if sort_col in table_df.columns:
        table_df = table_df.sort_values(sort_col, ascending=sort_asc, na_position='last')
    
    if not selected_funds:
        ytd_sorted = table_df.sort_values('YTD', ascending=False, na_position='last')
        selected_funds = ytd_sorted['fund_id'].head(4).tolist()
    
    since_label = pd.Timestamp(since_date).strftime('%d %b %y')
    
    sections = []
    for cat, group in table_df.groupby('Type', sort=False):
        sections.append(html.Div([
            html.P(cat.upper(), style={
                'color': '#1a3a5c', 'fontSize': '9px',
                'fontWeight': '700', 'letterSpacing': '0.06em',
                'textTransform': 'uppercase', 'marginBottom': '4px',
                'marginTop': '8px' if sections else '0',
                'borderBottom': '1px solid #e0e0e0', 'paddingBottom': '3px',
            }),
            html.Div(
                render_table(
                    group, since_label, sort_state,
                    selected_funds=selected_funds, clickable=True,
                    header_type='holdings'
                ),
                style={'overflowX': 'auto'}
            ),
        ]))
    
    return html.Div(sections), sort_state


@callback(
    Output('holdings-relative-chart', 'figure'),
    Output('holdings-chart-info', 'children'),
    Output('holdings-selected-funds', 'data'),
    Input('holdings-selected-funds', 'data'),
    Input('holdings-since-date', 'date'),
)
def update_holdings_chart(selected_funds, since_date):
    selected_funds = selected_funds or []
    since_date = since_date or '2026-03-01'
    
    if not selected_funds:
        portfolio = load_portfolio_holdings()
        if not portfolio.empty:
            holding_ids = portfolio['fund_id'].tolist()
            prices_all = load_prices(fund_ids=holding_ids)
            if not prices_all.empty:
                table_all = build_returns_table(prices_all, since_date)
                ytd_sorted = table_all.sort_values('YTD', ascending=False, na_position='last')
                selected_funds = ytd_sorted['fund_id'].head(4).tolist()
    
    count = len(selected_funds)
    
    if not selected_funds:
        fig = go.Figure()
        fig.add_annotation(
            text="Click a holding in the table to add it to the chart",
            x=0.5, y=0.5, xref='paper', yref='paper',
            showarrow=False, font=dict(size=12, color='#aaa')
        )
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=400, margin=dict(l=40, r=40, t=10, b=40))
        return fig, "No funds selected", selected_funds
    
    info = f"{count} fund{'s' if count != 1 else ''} selected"
    
    prices_df = load_prices(fund_ids=selected_funds)
    instruments_df = load_instruments(fund_ids=selected_funds)
    name_map = dict(zip(instruments_df['fund_id'], instruments_df['name']))
    
    if prices_df.empty:
        fig = go.Figure()
        fig.update_layout(height=400)
        return fig, info, selected_funds
    
    fig = go.Figure()
    start = pd.Timestamp(since_date)
    
    fund_returns = []
    for fid in selected_funds:
        r = calc_return(prices_df, fid, from_date=since_date)
        fund_returns.append((fid, r or -999))
    fund_returns.sort(key=lambda x: x[1], reverse=True)
    
    colours = ['#2E75B6', '#e67e22', '#1a7a1a', '#c0392b', '#8e44ad', '#16a085', '#d35400', '#2980b9']
    
    for i, (fund_id, _) in enumerate(fund_returns):
        fund_prices = prices_df[prices_df['fund_id'] == fund_id].sort_values('date')
        if fund_prices.empty:
            continue
        
        base_df = fund_prices[fund_prices['date'] <= start]
        base_price = base_df.iloc[-1]['close'] if not base_df.empty else fund_prices.iloc[0]['close']
        
        if base_price == 0:
            continue
        
        chart_df = fund_prices[fund_prices['date'] >= start].copy()
        if chart_df.empty or len(chart_df) < 2:
            continue
        
        chart_df['return'] = ((chart_df['close'] / base_price) - 1) * 100
        fund_name = name_map.get(fund_id, chart_df.iloc[0].get('fund_name', fund_id))
        colour = colours[i % len(colours)]
        
        fig.add_trace(go.Scatter(
            x=chart_df['date'], y=chart_df['return'],
            mode='lines', name=fund_name, line=dict(width=2.5, color=colour),
            hovertemplate='%{x|%d %b %Y}: %{y:.1f}%<extra>' + fund_name + '</extra>',
        ))
        
        idx_max = chart_df['return'].idxmax()
        idx_min = chart_df['return'].idxmin()
        last_row = chart_df.iloc[-1]
        
        for point, label, ay, font_colour in [
            (chart_df.loc[idx_max], f"H: {chart_df.loc[idx_max, 'return']:+.1f}%", -20, '#1a7a1a'),
            (chart_df.loc[idx_min], f"L: {chart_df.loc[idx_min, 'return']:+.1f}%", 20, '#c0392b'),
            (last_row, f"▶ {last_row['return']:+.1f}%", 0, '#1a3a5c'),
        ]:
            fig.add_annotation(
                x=point['date'], y=point['return'], text=label,
                showarrow=True, arrowhead=0, arrowwidth=1, ax=25, ay=ay,
                font=dict(size=8, color=font_colour),
                bgcolor='rgba(255,255,255,0.9)', bordercolor='#ddd', borderwidth=1, borderpad=3,
            )
    
    fig.update_layout(
        yaxis_tickformat='+.1f', yaxis_ticksuffix='%',
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.25, x=0, font=dict(size=10), bgcolor='rgba(255,255,255,0.9)'),
        margin=dict(l=40, r=60, t=10, b=80),
        plot_bgcolor='white', paper_bgcolor='white', height=400,
    )
    fig.update_xaxes(showgrid=True, gridcolor='#f0f0f0', tickfont=dict(size=10))
    fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', zeroline=True, zerolinecolor='#bbb', zerolinewidth=1, tickfont=dict(size=10))
    
    return fig, info, selected_funds