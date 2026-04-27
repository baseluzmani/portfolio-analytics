"""Database connection helper. Read-only access to the shared FTScrapper database."""

import sqlite3
import os

# Absolute path to the shared database in the FTScrapper project
DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "FTScrapper", "data", "funds.db")
)


def get_connection(readonly=True):
    """
    Get a SQLite connection with WAL mode for safe concurrent access.
    
    Args:
        readonly: If True (default), opens database in read-only mode.
                  The analytics dashboard never writes to the database.
    """
    if readonly:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10)
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
    
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def check_database():
    """Verify the database exists and has the expected tables."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    
    table_names = [t['name'] for t in tables]
    print(f"Connected to database: {DB_PATH}")
    print(f"Tables found: {', '.join(table_names)}")
    return table_names