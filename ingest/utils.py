"""
Utility functions for TMDB API and PostgreSQL connection.
"""

import os
import time
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# =============================================
# CONFIGURATION
# =============================================

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "tmdb_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

INGEST_DELAY = float(os.getenv("INGEST_DELAY", "0.1"))


# =============================================
# DATABASE HELPERS
# =============================================

def get_db_connection():
    """Create and return a new database connection."""
    return psycopg2.connect(**DB_CONFIG)


def execute_query(query, params=None, fetch=False):
    """Execute a single SQL query."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if fetch:
                return cur.fetchall()
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def execute_batch(query, data):
    """Execute a batch insert using execute_values."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, data)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# =============================================
# TMDB API HELPERS
# =============================================

def tmdb_request(endpoint, params=None):
    """Make a request to the TMDB API."""
    url = f"{TMDB_BASE_URL}{endpoint}"
    params = params or {}
    params["api_key"] = TMDB_API_KEY

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def rate_limit():
    time.sleep(INGEST_DELAY)
