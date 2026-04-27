"""Data Quality page — visualise price history completeness, gaps, and anomalies."""

import holidays
import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data.queries import load_prices, load_instruments

dash.register_page(__name__, path='/data-quality', name='Data Quality')


# ── Layout ─────────────────────────────────────────────────────

layout = html.Div([
    html.Div([
        html.H2("Data Quality", style={
            'color': '#1a3a5c', 'fontSize': '18px',
            'fontWeight': '700', 'marginBottom': '4px'
        }),
        html.P(
            "Check price data completeness and anomalies before trusting analytics.",
            style={'color': '#888', 'fontSize': '12px', 'marginTop': '0'}
        ),
    ], style={'marginBottom': '16px'}),
    
    # Controls
    html.Div([
        html.Div([
            html.Label("Period:", style={
                'fontSize': '11px', 'color': '#666', 'marginRight': '8px'
            }),
            dcc.Dropdown(
                id='dq-period',
                options=[
                    {'label': 'Last 30 Days', 'value': '30D'},
                    {'label': 'Last 90 Days', 'value': '90D'},
                    {'label': 'Last 6 Months', 'value': '6M'},
                    {'label': 'Last 1 Year', 'value': '1Y'},
                    {'label': 'All Data', 'value': 'ALL'},
                ],
                value='90D',
                clearable=False,
                style={'width': '150px', 'fontSize': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
        
        html.Div([
            html.Label("Min Gap (days):", style={
                'fontSize': '11px', 'color': '#666', 'marginRight': '8px'
            }),
            dcc.Dropdown(
                id='dq-min-gap',
                options=[
                    {'label': 'Any gap', 'value': 1},
                    {'label': '3+ days', 'value': 3},
                    {'label': '5+ days', 'value': 5},
                    {'label': '10+ days', 'value': 10},
                ],
                value=3,
                clearable=False,
                style={'width': '120px', 'fontSize': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
        
        html.Div([
            html.Label("Jump Threshold:", style={
                'fontSize': '11px', 'color': '#666', 'marginRight': '8px'
            }),
            dcc.Dropdown(
                id='dq-jump-threshold',
                options=[
                    {'label': '3% (sensitive)', 'value': 3},
                    {'label': '5% (moderate)', 'value': 5},
                    {'label': '10% (major only)', 'value': 10},
                    {'label': '20% (extreme)', 'value': 20},
                ],
                value=10,
                clearable=False,
                style={'width': '140px', 'fontSize': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
        
        html.Div([
            html.Label("Source:", style={
                'fontSize': '11px', 'color': '#666', 'marginRight': '8px'
            }),
            dcc.Dropdown(
                id='dq-source-filter',
                options=[
                    {'label': 'All Sources', 'value': 'ALL'},
                    {'label': 'Financial Times', 'value': 'FT'},
                    {'label': 'Yahoo Finance', 'value': 'YF'},
                    {'label': 'Composites', 'value': 'COMPOSITE'},
                    {'label': 'Calculated', 'value': 'CALC'},
                ],
                value='ALL',
                clearable=False,
                style={'width': '150px', 'fontSize': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center'}),
    ], style={
        'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap',
        'marginBottom': '16px', 'padding': '12px 16px',
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'boxShadow': '0 1px 4px rgba(0,0,0,0.08)'
    }),
    
    # Summary cards
    html.Div(id='dq-summary-cards', style={
        'display': 'flex', 'gap': '16px', 'marginBottom': '16px', 'flexWrap': 'wrap'
    }),
    
    # Gap timeline heatmap
    html.Div([
        html.H3("Gap Timeline", style={
            'color': '#1a3a5c', 'fontSize': '14px',
            'fontWeight': '600', 'marginBottom': '4px'
        }),
        html.P(id='dq-gap-info', style={
            'color': '#888', 'fontSize': '11px', 'marginTop': '0'
        }),
        dcc.Graph(
            id='dq-gap-heatmap',
            config={'displayModeBar': True},
            style={'height': '500px'}
        ),
    ], style={
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'padding': '14px 18px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
        'marginBottom': '16px'
    }),
    
    # Price jumps table
    html.Div([
        html.H3("Price Jumps (Potential Data Errors)", style={
            'color': '#1a3a5c', 'fontSize': '14px',
            'fontWeight': '600', 'marginBottom': '4px'
        }),
        html.P(id='dq-jump-info', style={
            'color': '#888', 'fontSize': '11px', 'marginTop': '0'
        }),
        html.Div(id='dq-jumps-table'),
    ], style={
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'padding': '14px 18px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
        'marginBottom': '16px'
    }),
    
    # Per-fund detail table
    html.Div([
        html.H3("Fund Detail", style={
            'color': '#1a3a5c', 'fontSize': '14px',
            'fontWeight': '600', 'marginBottom': '8px'
        }),
        html.Div(id='dq-detail-table'),
    ], style={
        'backgroundColor': '#fff', 'borderRadius': '8px',
        'padding': '14px 18px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
    }),
])


# ── Callbacks ──────────────────────────────────────────────────

@callback(
    Output('dq-summary-cards', 'children'),
    Output('dq-gap-heatmap', 'figure'),
    Output('dq-gap-info', 'children'),
    Output('dq-jumps-table', 'children'),
    Output('dq-jump-info', 'children'),
    Output('dq-detail-table', 'children'),
    Input('dq-period', 'value'),
    Input('dq-min-gap', 'value'),
    Input('dq-jump-threshold', 'value'),
    Input('dq-source-filter', 'value'),
)
def update_data_quality(period, min_gap_days, jump_threshold_pct, source_filter):
    # ── 1. Load data ─────────────────────────────────────────
    all_prices = load_prices()
    
    if all_prices.empty:
        return _empty_cards(), _empty_figure("No price data in database."), "", "", "", ""
    
    # Filter by date range
    today = datetime.today()
    period_map = {
        '30D': today - timedelta(days=30),
        '90D': today - timedelta(days=90),
        '6M': today - timedelta(days=180),
        '1Y': today - timedelta(days=365),
        'ALL': all_prices['date'].min(),
    }
    cutoff = period_map.get(period, period_map['90D'])
    
    prices_df = all_prices[all_prices['date'] >= pd.Timestamp(cutoff)].copy()
    
    if prices_df.empty:
        return _empty_cards(), _empty_figure("No data in selected period."), "", "", "", ""
    
    # ── 2. Filter by source ──────────────────────────────────
    if source_filter != 'ALL':
        if source_filter == 'FT':
            prices_df = prices_df[
                prices_df['fund_id'].str.match(r'^[A-Z]{2}[A-Z0-9]{10}:') &
                ~prices_df['fund_id'].str.startswith('YF:')
            ]
        elif source_filter == 'YF':
            prices_df = prices_df[prices_df['fund_id'].str.startswith('YF:')]
        elif source_filter == 'COMPOSITE':
            prices_df = prices_df[prices_df['fund_id'].str.startswith('COMPOSITE:')]
        elif source_filter == 'CALC':
            prices_df = prices_df[prices_df['fund_id'].str.startswith('CALC:')]
    
    if prices_df.empty:
        return _empty_cards(), _empty_figure("No data for selected source."), "", "", "", ""
    
    # ── 3. Build completeness per fund ────────────────────────
        # ── 3. Build completeness per fund ────────────────────────
    instruments_df = load_instruments(fund_ids=prices_df['fund_id'].unique().tolist())
    instruments_indexed = instruments_df.set_index('fund_id')
    name_map = dict(zip(instruments_df['fund_id'], instruments_df['name']))
    
    # Get the full date range (all calendar days, we filter per-fund)
    all_dates = pd.date_range(
        start=prices_df['date'].min(),
        end=prices_df['date'].max(),
        freq='D'
    )
    
    years = list(set(d.year for d in all_dates))
    
    # Pre-load holidays for each country we'll need
    holiday_cache = {}
    
    fund_stats = []
    gap_data = []
    
    for fund_id, group in prices_df.groupby('fund_id'):
        fund_name = name_map.get(fund_id, group['fund_name'].iloc[0] if 'fund_name' in group.columns else fund_id)
        category = group['category'].iloc[0] if 'category' in group.columns else ''
        
        # Determine trading country for this fund
        country = _get_trading_country(fund_id, instruments_indexed)
        
        # Get holidays for this country (cached)
        if country and country not in holiday_cache:
            holiday_cache[country] = _get_holidays_for_country(country, years)
        
        country_holidays = holiday_cache.get(country, set())
        
        # Build expected trading days: weekdays minus country holidays
        expected_dates = set()
        holiday_dates = set()
        weekend_dates = set()
        
        for d in all_dates:
            d_date = d.date()
            if d.weekday() >= 5:  # Saturday or Sunday
                weekend_dates.add(d_date)
            elif d_date in country_holidays:
                holiday_dates.add(d_date)
            else:
                expected_dates.add(d_date)
        
        actual_dates = set(group['date'].dt.date)
        
        missing_expected = sorted(expected_dates - actual_dates)
        present_count = len(actual_dates & expected_dates)
        total_expected = len(expected_dates)
        completeness = (present_count / total_expected * 100) if total_expected > 0 else 0
        
        gaps = _find_gaps(missing_expected, min_gap_days)
        max_gap = max(gaps) if gaps else 0
        
        # Count holidays and weekends for display
        num_holidays = len(set(d for d in holiday_dates if d >= all_dates[0].date() and d <= all_dates[-1].date()))
        num_weekends = len(set(d for d in weekend_dates if d >= all_dates[0].date() and d <= all_dates[-1].date()))
        
        fund_stats.append({
            'fund_id': fund_id,
            'fund_name': fund_name,
            'category': category,
            'country': country or 'Unknown',
            'total_expected': total_expected,
            'present': present_count,
            'missing': total_expected - present_count,
            'completeness': completeness,
            'gaps': gaps,
            'max_gap': max_gap,
            'first_date': group['date'].min(),
            'last_date': group['date'].max(),
            'num_holidays': num_holidays,
            'num_weekends': num_weekends,
        })
        
        # Build daily presence for heatmap (all days, coded by type)
        for d in all_dates:
            d_date = d.date()
            if d_date in actual_dates:
                status = 2  # Present
            elif d_date in holiday_dates:
                status = 1  # Holiday (expected gap)
            elif d_date in weekend_dates:
                status = 1  # Weekend (expected gap)
            else:
                status = 0  # Missing (unexpected gap)
            
            gap_data.append({
                'fund_id': fund_id,
                'fund_name': fund_name,
                'date': d,
                'status': status,
                'is_expected_gap': status == 1,
                'is_missing': status == 0,
            })
    
    stats_df = pd.DataFrame(fund_stats).sort_values('completeness')
    gap_df = pd.DataFrame(gap_data)
    
    
    # ── 4. Detect price jumps ─────────────────────────────────
    jumps_list = _detect_jumps(prices_df, name_map, jump_threshold_pct, min_gap_days, cutoff)
    jumps_df = pd.DataFrame(jumps_list) if jumps_list else pd.DataFrame()
    
    # ── 5. Summary cards ──────────────────────────────────────
    total_funds = len(stats_df)
    avg_completeness = stats_df['completeness'].mean() if total_funds > 0 else 0
    funds_with_gaps = len(stats_df[stats_df['max_gap'] >= min_gap_days])
    total_jumps = len(jumps_df)
    
    cards = [
        _summary_card("Total Funds", str(total_funds), "#1a3a5c"),
        _summary_card("Avg Completeness", f"{avg_completeness:.1f}%",
                      "#1a7a1a" if avg_completeness > 95 else "#e67e22" if avg_completeness > 80 else "#c0392b"),
        _summary_card("Funds with Gaps", str(funds_with_gaps),
                      "#1a7a1a" if funds_with_gaps == 0 else "#c0392b"),
        _summary_card("Price Jumps Found", str(total_jumps),
                      "#1a7a1a" if total_jumps == 0 else "#c0392b"),
    ]
    
    # ── 6. Gap timeline heatmap ───────────────────────────────
    fig = _build_gap_heatmap(gap_df, stats_df, min_gap_days, name_map)
    
    gap_info = (
        f"Showing {len(stats_df[stats_df['max_gap'] >= min_gap_days])} funds with gaps ≥ {min_gap_days} business days. "
        f"Green = data present, Red = missing. Some gaps may be weekends/holidays."
    )
    
    # ── 7. Jumps table ────────────────────────────────────────
    if not jumps_list:
        jumps_table = html.P(
            f"No price jumps ≥ {jump_threshold_pct}% detected in the selected period.",
            style={'color': '#1a7a1a', 'fontSize': '12px', 'fontWeight': '500'}
        )
        jump_info = f"Looking for single-day price changes ≥ ±{jump_threshold_pct}%."
    else:
        jump_info = f"Found {len(jumps_list)} single-day price changes ≥ ±{jump_threshold_pct}%. These may indicate data errors."
        jumps_table = _build_jumps_table(jumps_list, name_map, jump_threshold_pct)
    
    # ── 8. Detail table ───────────────────────────────────────
    detail_table = _build_detail_table(stats_df, min_gap_days)
    
    return cards, fig, gap_info, jumps_table, jump_info, detail_table


# ── Jump Detection ─────────────────────────────────────────────

def _detect_jumps(prices_df, name_map, threshold_pct, min_gap_days, cutoff_date):
    """
    Detect single-day price jumps exceeding threshold_pct.
    Excludes jumps caused by gaps (where a large move is expected).
    """
    jumps = []
    
    for fund_id, group in prices_df.groupby('fund_id'):
        group = group.sort_values('date').copy()
        group['prev_close'] = group['close'].shift(1)
        group['pct_change'] = (group['close'] - group['prev_close']) / group['prev_close'] * 100
        group['days_since_prev'] = (group['date'] - group['date'].shift(1)).dt.days
        
        # Flag jumps that exceed threshold
        anomalies = group[
            (group['pct_change'].abs() >= threshold_pct) &
            group['prev_close'].notna() &
            # Exclude jumps after gaps (expected if market moved while data was missing)
            (group['days_since_prev'] <= min_gap_days + 2)
        ]
        
        for _, row in anomalies.iterrows():
            jumps.append({
                'fund_id': fund_id,
                'fund_name': name_map.get(fund_id, fund_id),
                'date': row['date'],
                'close': row['close'],
                'prev_close': row['prev_close'],
                'pct_change': round(row['pct_change'], 2),
                'days_since_prev': int(row['days_since_prev']) if pd.notna(row['days_since_prev']) else 1,
            })
    
    # Sort by absolute % change descending
    return sorted(jumps, key=lambda x: abs(x['pct_change']), reverse=True)

def _get_trading_country(fund_id, instruments_df):
    """
    Determine the trading country for a fund based on its currency or fund_id prefix.
    
    Returns an ISO country code ('GB', 'US', 'TR', etc.) or None if unknown.
    """
    # If we have instrument metadata with currency
    if fund_id in instruments_df.index:
        currency = instruments_df.loc[fund_id, 'currency'] if 'currency' in instruments_df.columns else None
        if currency:
            currency_map = {
                'GBP': 'GB', 'GBX': 'GB', 'GBPC': 'GB',
                'USD': 'US',
                'TRY': 'TR',
                'EUR': 'EU',
            }
            return currency_map.get(str(currency).upper())
    
    # Fallback: guess from ticker suffix
    if fund_id.endswith('.L') or fund_id.endswith('.IL'):
        return 'GB'  # London listed
    if fund_id.endswith('.IS'):
        return 'TR'  # Istanbul listed
    if ':' in fund_id:
        suffix = fund_id.split(':')[-1]
        if suffix in ('GBP', 'GBX', 'GBPC'):
            return 'GB'
        if suffix == 'USD':
            return 'US'
    
    # FT funds (ISIN:GBP format) are UK
    if fund_id.startswith('GB') and ':' in fund_id:
        return 'GB'
    
    return None


def _get_holidays_for_country(country_code, years):
    """
    Get holidays for a country across given years.
    Includes relevant market-specific holidays.
    """
    if not country_code:
        return set()
    
    try:
        if country_code == 'GB':
            # UK market holidays (England, plus some UK-wide)
            hols = holidays.UK(subdiv='England', years=years)
        elif country_code == 'US':
            # US market holidays (NYSE observes these)
            hols = holidays.US(years=years)
            # NYSE doesn't observe all federal holidays, but for our purposes
            # including all US holidays is a reasonable proxy
        elif country_code == 'TR':
            hols = holidays.TR(years=years)
        elif country_code == 'EU':
            # Use ECB/TARGET2 holidays (major European markets)
            hols = holidays.EuropeanCentralBank(years=years)
        else:
            # Try generic country code
            hols = holidays.country_holidays(country_code, years=years)
        
        return {d for d in hols.keys()}
    except Exception:
        return set()

def _build_jumps_table(jumps_list, name_map, threshold_pct):
    """Build HTML table for price jumps from a list of dicts."""
    if not jumps_list:
        return html.P(
            f"No price jumps ≥ {threshold_pct}% detected in the selected period.",
            style={'color': '#1a7a1a', 'fontSize': '12px', 'fontWeight': '500'}
        )
    
    rows = []
    for j in jumps_list:
        pct = j['pct_change']
        if abs(pct) >= 20:
            severity = '🔴 Extreme'
            bg = '#ffebee'
            color = '#b71c1c'
        elif abs(pct) >= 10:
            severity = '🟠 Major'
            bg = '#fff3e0'
            color = '#e65100'
        else:
            severity = '🟡 Moderate'
            bg = '#fffde7'
            color = '#f57f17'
        
        direction = '▲' if pct > 0 else '▼'
        rows.append(html.Tr([
            html.Td(j['fund_name'][:35], style={'padding': '6px 8px', 'fontSize': '12px', 'color': '#1a3a5c'}),
            html.Td(j['date'].strftime('%d %b %Y'), style={
                'padding': '6px 8px', 'fontSize': '11px', 'textAlign': 'center',
                'fontFamily': 'monospace'
            }),
            html.Td(f"{j['prev_close']:.4f}", style={
                'padding': '6px 8px', 'fontSize': '11px', 'textAlign': 'right',
                'fontFamily': 'monospace', 'color': '#888'
            }),
            html.Td(f"{j['close']:.4f}", style={
                'padding': '6px 8px', 'fontSize': '11px', 'textAlign': 'right',
                'fontFamily': 'monospace', 'color': '#888'
            }),
            html.Td(f"{direction} {abs(pct):.1f}%", style={
                'padding': '6px 8px', 'fontSize': '12px', 'textAlign': 'center',
                'fontFamily': 'monospace', 'fontWeight': '700',
                'color': color, 'backgroundColor': bg, 'borderRadius': '3px'
            }),
            html.Td(severity, style={
                'padding': '6px 8px', 'fontSize': '11px', 'textAlign': 'center'
            }),
        ]))
    
    return html.Table(
        [html.Thead(html.Tr([
            html.Th("Fund", style=th_style),
            html.Th("Date", style=th_style),
            html.Th("Prev Close", style=th_style),
            html.Th("Close", style=th_style),
            html.Th("Change", style=th_style),
            html.Th("Severity", style=th_style),
        ])),
        html.Tbody(rows),
    ], style={'width': '100%', 'borderCollapse': 'collapse'})

# ── Helper functions (unchanged from previous version) ─────────

def _find_gaps(missing_dates, min_gap_days):
    if not missing_dates:
        return []
    
    gaps = []
    current_gap = 1
    
    for i in range(1, len(missing_dates)):
        if (missing_dates[i] - missing_dates[i-1]).days <= 3:
            current_gap += 1
        else:
            if current_gap >= min_gap_days:
                gaps.append(current_gap)
            current_gap = 1
    
    if current_gap >= min_gap_days:
        gaps.append(current_gap)
    
    return gaps

def _build_gap_heatmap(gap_df, stats_df, min_gap_days, name_map):
    if gap_df.empty:
        return _empty_figure("No data to display.")
    
    fund_order = stats_df['fund_id'].tolist()
    
    # Use 'status' column: 0=missing, 1=holiday/weekend, 2=present
    pivot = gap_df.pivot_table(
        index='fund_id', columns='date', values='status', aggfunc='first'
    )
    pivot = pivot.reindex(fund_order)
    
    funds_with_gaps = stats_df[stats_df['max_gap'] >= min_gap_days]['fund_id'].tolist()
    
    if not funds_with_gaps:
        fig = go.Figure()
        fig.add_annotation(
            text="No unexpected gaps detected! All trading days have data.",
            x=0.5, y=0.5, xref='paper', yref='paper',
            showarrow=False, font=dict(size=14, color='#1a7a1a')
        )
        fig.update_layout(height=300, plot_bgcolor='white', paper_bgcolor='white')
        return fig
    
    pivot = pivot.loc[funds_with_gaps]
    labels = [name_map.get(fid, fid)[:35] for fid in pivot.index]
    
    # Three-colour scale: 0=red (unexpected gap), 1=grey (holiday/weekend), 2=green (data)
    colorscale = [
        [0.0, '#dc3545'],    # Missing trading day
        [0.5, '#d3d3d3'],    # Holiday/weekend
        [1.0, '#28a745'],    # Data present
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=labels,
        zmin=0, zmax=2,
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(
            title=dict(text='Status', side='right'),
            ticktext=['Missing', 'Holiday/Weekend', 'Present'],
            tickvals=[0.33, 1.0, 1.67],
            thickness=15,
            len=0.6,
        ),
        hoverongaps=False,
        hovertemplate=(
            '%{y}<br>%{x|%d %b %Y}<br>'
            '%{z:missing (unexpected)|holiday/weekend|data present}<extra></extra>'
        ),
    ))
    
    fig.update_layout(
        xaxis={'tickfont': {'size': 8}, 'tickangle': -45},
        yaxis={'tickfont': {'size': 9}},
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=10, r=50, t=10, b=80),
        height=max(300, 60 + len(funds_with_gaps) * 25),
    )
    
    return fig


def _build_detail_table(stats_df, min_gap_days):
    if stats_df.empty:
        return html.P("No data available.", style={'color': '#888'})
    
    rows = []
    for _, row in stats_df.iterrows():
        completeness = row['completeness']
        if completeness >= 95:
            color = '#1a7a1a'; bg = '#e8f5e9'
        elif completeness >= 80:
            color = '#e67e22'; bg = '#fff3e0'
        else:
            color = '#c0392b'; bg = '#ffebee'
        
        gap_str = ', '.join(f"{g}d" for g in row['gaps'][:3])
        if len(row['gaps']) > 3:
            gap_str += f" +{len(row['gaps']) - 3} more"
        
        rows.append(html.Tr([
            html.Td(row['fund_name'][:40], style={'padding': '5px 8px', 'fontSize': '12px', 'color': '#1a3a5c'}),
            html.Td(row.get('country', '?'), style={'padding': '5px 4px', 'fontSize': '10px', 'color': '#888', 'textAlign': 'center'}),
            html.Td(row['category'] or '—', style={'padding': '5px 8px', 'fontSize': '11px', 'color': '#666', 'textAlign': 'center'}),
            html.Td(row['first_date'].strftime('%d %b %Y'), style={'padding': '5px 8px', 'fontSize': '11px', 'fontFamily': 'monospace', 'textAlign': 'center'}),
            html.Td(row['last_date'].strftime('%d %b %Y'), style={'padding': '5px 8px', 'fontSize': '11px', 'fontFamily': 'monospace', 'textAlign': 'center'}),
            html.Td(f"{row['present']} / {row['total_expected']}", style={'padding': '5px 8px', 'fontSize': '11px', 'fontFamily': 'monospace', 'textAlign': 'center'}),
            html.Td(f"{completeness:.1f}%", style={'padding': '5px 8px', 'fontSize': '11px', 'fontFamily': 'monospace', 'fontWeight': '700', 'textAlign': 'center', 'backgroundColor': bg, 'color': color, 'borderRadius': '3px'}),
            html.Td(str(row.get('num_holidays', 0)), style={'padding': '5px 4px', 'fontSize': '10px', 'color': '#999', 'textAlign': 'center'}),
            html.Td(gap_str if row['gaps'] else 'None', style={'padding': '5px 8px', 'fontSize': '10px', 'color': '#c0392b' if row['gaps'] else '#1a7a1a', 'textAlign': 'center'}),
        ]))
    
    return html.Table(
        [html.Thead(html.Tr([
            html.Th("Fund", style=th_style),
            html.Th("Ctry", style=th_style),
            html.Th("Category", style=th_style),
            html.Th("First Data", style=th_style),
            html.Th("Last Data", style=th_style),
            html.Th("Coverage", style=th_style),
            html.Th("Complete", style=th_style),
            html.Th("Gaps", style=th_style),
        ])), html.Tbody(rows)],
        style={'width': '100%', 'borderCollapse': 'collapse'}
    )


def _summary_card(title, value, color):
    return html.Div([
        html.P(title, style={'fontSize': '10px', 'color': '#999', 'margin': '0', 'textTransform': 'uppercase', 'letterSpacing': '0.05em'}),
        html.P(value, style={'fontSize': '22px', 'fontWeight': '700', 'color': color, 'margin': '4px 0 0 0'}),
    ], style={'flex': '1', 'minWidth': '160px', 'backgroundColor': '#fff', 'borderRadius': '8px', 'padding': '14px 18px', 'boxShadow': '0 1px 4px rgba(0,0,0,0.08)'})


def _empty_cards():
    return [_summary_card("Total Funds", "0", "#1a3a5c"), _summary_card("Avg Completeness", "N/A", "#666"), _summary_card("Funds with Gaps", "0", "#1a3a5c"), _summary_card("Price Jumps Found", "0", "#1a3a5c")]


def _empty_figure(message):
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False, font=dict(size=14, color='#999'))
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=300, margin=dict(l=40, r=40, t=40, b=40))
    return fig


th_style = {'backgroundColor': '#1a3a5c', 'color': 'white', 'padding': '6px 8px', 'fontSize': '10px', 'fontWeight': '600', 'textAlign': 'center', 'whiteSpace': 'nowrap'}