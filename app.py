"""
Portfolio Analytics Dashboard
Run with: python3 app.py
Then open: http://localhost:8051
"""

import dash
from dash import html, dcc

app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.title = "Portfolio Analytics"

# ── Styles ─────────────────────────────────────────────────────

link_style = {
    'padding': '8px 16px',
    'fontSize': '12px',
    'fontWeight': '600',
    'color': '#666',
    'textDecoration': 'none',
    'borderRadius': '4px',
    'backgroundColor': 'transparent',
    'transition': 'background-color 0.2s',
}

# ── Layout ─────────────────────────────────────────────────────

app.layout = html.Div([
    # Header
    html.Div([
        html.Div([
            html.Span("PORTFOLIO", style={
                'color': '#2E75B6', 'fontWeight': '800',
                'fontSize': '18px', 'letterSpacing': '0.1em',
            }),
            html.Span(" ANALYTICS", style={
                'color': '#1a3a5c', 'fontWeight': '300',
                'fontSize': '18px', 'letterSpacing': '0.1em',
            }),
        ]),
        html.Span(
            "Data as of loading...",
            id='data-date-label',
            style={'fontSize': '11px', 'color': '#999', 'alignSelf': 'center'}
        ),
    ], style={
        'display': 'flex', 'justifyContent': 'space-between',
        'alignItems': 'center', 'padding': '12px 20px',
        'backgroundColor': '#fff', 'borderBottom': '2px solid #2E75B6',
        'marginBottom': '0',
    }),
    
    # Navigation tabs
    html.Div([
        dcc.Link('Correlation Matrix', href='/correlation', style=link_style),
        dcc.Link('Return Clusters', href='/clustering', style=link_style),
        dcc.Link('Overlap Detector', href='/overlap-detector', style=link_style),
        dcc.Link('Data Quality', href='/data-quality', style=link_style),
    ], style={
        'display': 'flex', 'gap': '4px',
        'padding': '8px 20px', 'backgroundColor': '#f8f9fa',
        'borderBottom': '1px solid #e0e0e0',
    }),
    
    # Page content
    dash.page_container,
    
], style={
    'fontFamily': '"DM Sans", -apple-system, BlinkMacSystemFont, sans-serif',
    'backgroundColor': '#f0f3f7',
    'minHeight': '100vh',
})

# ── Run ────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Check database connection before starting
    from data.connection import check_database
    try:
        check_database()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Make sure FTScrapper/data/funds.db exists.")
        exit(1)
    
    print("\nStarting Portfolio Analytics Dashboard...")
    print("Open http://localhost:8051 in your browser")
    app.run(host="0.0.0.0", port=8051, debug=True)