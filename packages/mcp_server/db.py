from pathlib import Path
import os

import psycopg

from dotenv import load_dotenv


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Return a PostgreSQL connection using the TT&T .env file.
    """

    return psycopg.connect(
        **DB_CONFIG
    )