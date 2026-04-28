"""Return calculations shared across pages."""

import pandas as pd
from datetime import datetime, timedelta


def get_latest_price(df, fund_id):
    """Get the most recent closing price for a fund."""
    fund_df = df[df['fund_id'] == fund_id]
    if fund_df.empty:
        return None
    return fund_df.loc[fund_df['date'].idxmax(), 'close']


def calc_return(df, fund_id, days_back=None, from_date=None):
    """Calculate percentage return for a fund over a period."""
    fund_df = df[df['fund_id'] == fund_id].sort_values('date')
    if fund_df.empty:
        return None
    
    latest_price = fund_df.iloc[-1]['close']
    
    if from_date:
        past_df = fund_df[fund_df['date'] <= pd.Timestamp(from_date)]
    else:
        past_df = fund_df[fund_df['date'] <= fund_df['date'].max() - timedelta(days=days_back)]
    
    if past_df.empty:
        return None
    
    past_price = past_df.iloc[-1]['close']
    if past_price == 0:
        return None
    
    return ((latest_price / past_price) - 1) * 100


def ytd_date():
    """Get the last trading day of the previous year."""
    dec31 = datetime(datetime.now().year - 1, 12, 31)
    while dec31.weekday() >= 5:
        dec31 -= timedelta(days=1)
    return dec31.strftime('%Y-%m-%d')


def build_returns_table(df, since_date):
    """
    Build a returns table for all funds in the dataframe.
    
    Args:
        df: DataFrame with columns [fund_id, fund_name, asset_type, date, close]
        since_date: Base date for 'Since' return column
    
    Returns:
        DataFrame with columns [fund_id, Fund, Type, Price, 1D, 1W, 1M, 3M, YTD, Since]
    """
    funds = df[['fund_id', 'fund_name', 'asset_type']].drop_duplicates(subset=['fund_id'])
    rows = []
    
    for _, fund in funds.iterrows():
        fid = fund['fund_id']
        fname = fund['fund_name']
        atype = fund['asset_type'] if pd.notna(fund['asset_type']) else '—'
        latest = get_latest_price(df, fid)
        
        rows.append({
            'fund_id': fid,
            'Fund': fname,
            'Type': atype,
            'Price': round(latest, 2) if latest else None,
            '1D': calc_return(df, fid, days_back=1),
            '1W': calc_return(df, fid, days_back=5),
            '1M': calc_return(df, fid, days_back=21),
            '3M': calc_return(df, fid, days_back=63),
            'YTD': calc_return(df, fid, from_date=ytd_date()),
            'Since': calc_return(df, fid, from_date=since_date),
        })
    
    result = pd.DataFrame(rows)
    result = result.sort_values('YTD', ascending=False, na_position='last')
    return result