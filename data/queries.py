"""Read-only SQL queries for the analytics dashboard."""

import pandas as pd
from .connection import get_connection

def load_prices(fund_ids=None, min_date=None):
    """
    Load price history for specified funds.
    
    Args:
        fund_ids: List of fund_ids, or None for all.
        min_date: Optional earliest date (YYYY-MM-DD).
    
    Returns:
        DataFrame with columns: fund_id, fund_name, asset_type, category, date, close
    """
    conn = get_connection()
    
    query = """
        SELECT p.fund_id, i.name AS fund_name, i.asset_type, i.category, 
               p.date, p.close
        FROM prices p
        JOIN instruments i ON p.fund_id = i.fund_id
        WHERE 1=1
    """
    params = []
    
    if fund_ids:
        placeholders = ','.join(['?' for _ in fund_ids])
        query += f" AND p.fund_id IN ({placeholders})"
        params.extend(fund_ids)
    
    if min_date:
        query += " AND p.date >= ?"
        params.append(min_date)
    
    query += " ORDER BY p.fund_id, p.date"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    df['date'] = pd.to_datetime(df['date'])
    return df

def load_portfolio_holdings():
    """
    Load current portfolio holdings with current units > 0.
    
    Returns:
        DataFrame with columns: fund_id, units, name, category, currency
    """
    conn = get_connection()
    
    query = """
        SELECT h.fund_id, h.units, i.name, i.category, i.currency, i.price_unit
        FROM portfolio_holdings h
        JOIN instruments i ON h.fund_id = i.fund_id
        WHERE h.units > 0
        ORDER BY i.category, i.name
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def load_instruments(fund_ids=None):
    """
    Load instrument metadata.
    
    Args:
        fund_ids: Optional list of fund_ids to filter.
    
    Returns:
        DataFrame with columns: fund_id, name, asset_type, currency, price_unit, category
    """
    conn = get_connection()
    
    query = "SELECT fund_id, name, asset_type, currency, price_unit, category FROM instruments"
    params = []
    
    if fund_ids:
        placeholders = ','.join(['?' for _ in fund_ids])
        query += f" WHERE fund_id IN ({placeholders})"
        params.extend(fund_ids)
    
    query += " ORDER BY category, name"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_date_range(fund_ids=None):
    """
    Get the earliest and latest dates in the price data.
    
    Returns:
        Tuple of (min_date, max_date) as datetime objects, or (None, None).
    """
    conn = get_connection()
    
    query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM prices"
    params = []
    
    if fund_ids:
        placeholders = ','.join(['?' for _ in fund_ids])
        query += f" WHERE fund_id IN ({placeholders})"
        params.extend(fund_ids)
    
    row = conn.execute(query, params).fetchone()
    conn.close()
    
    if row and row['min_date']:
        return pd.to_datetime(row['min_date']), pd.to_datetime(row['max_date'])
    return None, None