"""Correlation matrix calculations for portfolio holdings."""

import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list


def build_return_series(prices_df, min_days=20):
    """
    Convert price history into daily return series per fund.
    
    Args:
        prices_df: DataFrame with columns [fund_id, date, close].
        min_days: Minimum number of trading days required to include a fund.
    
    Returns:
        DataFrame: One column per fund_id, rows = dates, values = daily returns.
        Funds with fewer than min_days are excluded.
    """
    returns = {}
    
    for fund_id, group in prices_df.groupby('fund_id'):
        group = group.sort_values('date').drop_duplicates('date')
        group['return'] = group['close'].pct_change()
        
        if group['return'].notna().sum() >= min_days:
            returns[fund_id] = group.set_index('date')['return']
    
    if not returns:
        return pd.DataFrame()
    
    return pd.DataFrame(returns)


def correlation_matrix(returns_df, method='pearson', min_overlap=30):
    """
    Calculate correlation matrix from return series.
    
    Args:
        returns_df: DataFrame of daily returns (funds as columns, dates as rows).
        method: 'pearson' for linear correlation, 'spearman' for rank correlation.
        min_overlap: Minimum overlapping data points for a valid correlation.
    
    Returns:
        DataFrame: Correlation matrix (funds × funds).
    """
    if returns_df.empty:
        return pd.DataFrame()
    
    if method == 'spearman':
        corr = returns_df.corr(method='spearman', min_periods=min_overlap)
    else:
        corr = returns_df.corr(method='pearson', min_periods=min_overlap)
    
    return corr


def correlation_with_benchmark(returns_df, benchmark_id):
    """
    Calculate each holding's correlation with a specific benchmark.
    
    Args:
        returns_df: DataFrame of daily returns.
        benchmark_id: The fund_id to use as benchmark (e.g., 'YF:^GSPC').
    
    Returns:
        DataFrame sorted by correlation descending.
    """
    if benchmark_id not in returns_df.columns:
        return pd.DataFrame()
    
    bench_returns = returns_df[benchmark_id]
    correlations = {}
    
    for col in returns_df.columns:
        if col == benchmark_id:
            continue
        valid = returns_df[[col, benchmark_id]].dropna()
        if len(valid) >= 20:
            correlations[col] = valid[col].corr(valid[benchmark_id])
    
    result = pd.DataFrame(
        list(correlations.items()),
        columns=['fund_id', 'correlation']
    ).sort_values('correlation', ascending=False)
    
    return result


def cluster_ordering(corr_matrix):
    """
    Use hierarchical clustering to order funds by return similarity.
    
    Args:
        corr_matrix: Correlation matrix (DataFrame).
    
    Returns:
        List of fund_ids in clustered order.
    """
    from scipy.spatial.distance import squareform
    
    # Convert correlation to distance: d = sqrt(2 * (1 - r))
    distance = np.sqrt(2 * (1 - corr_matrix.fillna(0)))
    
    # Handle perfect correlations (distance = 0)
    distance = distance.replace(0, 1e-10)
    
    # Convert square matrix to condensed form for scipy
    condensed = squareform(distance.values, checks=False)
    
    linkage_matrix = linkage(condensed, method='ward')
    ordered_indices = leaves_list(linkage_matrix)
    
    return [corr_matrix.columns[i] for i in ordered_indices]

def top_overlap_pairs(corr_matrix, min_correlation=0.7):
    """
    Find pairs of holdings with the highest correlations.
    
    Args:
        corr_matrix: Correlation matrix (DataFrame).
        min_correlation: Only return pairs above this threshold.
    
    Returns:
        DataFrame with columns: fund_1, fund_2, correlation.
    """
    pairs = []
    
    for i, fund1 in enumerate(corr_matrix.columns):
        for j, fund2 in enumerate(corr_matrix.columns):
            if i < j:  # Only upper triangle
                corr_val = corr_matrix.loc[fund1, fund2]
                if pd.notna(corr_val) and corr_val >= min_correlation:
                    pairs.append({
                        'fund_1': fund1,
                        'fund_2': fund2,
                        'correlation': round(corr_val, 4)
                    })
    
    if not pairs:
        return pd.DataFrame()
    
    return pd.DataFrame(pairs).sort_values('correlation', ascending=False)