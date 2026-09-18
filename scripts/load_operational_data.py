from pathlib import Path
import json
import os

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from dotenv import load_dotenv


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

OPERATIONAL_DIR = ROOT / "data" / "operational"

load_dotenv(ROOT / ".env")


# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}


# ---------------------------------------------------------
# IMPORTANT:
# Load parent tables before child tables because of
# foreign-key relationships.
# ---------------------------------------------------------

LOAD_ORDER = [
    ("users.json", "users"),
    ("accounts.json", "accounts"),
    ("plans.json", "plans"),
    ("lines.json", "lines"),
    ("subscriptions.json", "subscriptions"),
    ("devices.json", "devices"),
    ("invoices.json", "invoices"),
    ("invoice_items.json", "invoice_items"),
    ("payments.json", "payments"),
    ("usage_records.json", "usage_records"),
    ("outages.json", "outages"),
    ("support_tickets.json", "support_tickets"),
    ("connection_requests.json", "connection_requests"),
    ("orders.json", "orders"),
    ("activations.json", "activations"),
    ("number_port_requests.json", "number_port_requests"),
    ("account_history.json", "account_history"),
    ("runs.json", "runs"),
    ("audit_events.json", "audit_events"),
]


def load_json(path: Path):
    """
    Accept JSON formatted as:

    [
        {...},
        {...}
    ]

    or:

    {
        "records": [...]
    }

    or:

    {
        "users": [...]
    }
    """

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        # Common wrapper
        if "records" in data and isinstance(data["records"], list):
            return data["records"]

        # Find first list value
        for value in data.values():
            if isinstance(value, list):
                return value

        # Single object
        return [data]

    raise ValueError(f"Unsupported JSON structure: {path}")


def get_table_columns(conn, table_name: str):
    """
    Ask PostgreSQL which columns really exist in the table.
    """

    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position;
    """

    with conn.cursor() as cur:
        cur.execute(query, (table_name,))
        return {row[0] for row in cur.fetchall()}


def adapt_value(value):
    """
    Convert Python dictionaries/lists into JSONB-compatible
    PostgreSQL values.
    """

    if isinstance(value, (dict, list)):
        return Jsonb(value)

    return value


def insert_records(conn, table_name: str, records: list[dict]):

    if not records:
        print(f"[SKIP] {table_name}: no records")
        return

    table_columns = get_table_columns(conn, table_name)

    if not table_columns:
        print(f"[ERROR] PostgreSQL table '{table_name}' does not exist.")
        return

    inserted = 0

    for index, record in enumerate(records, start=1):

        # Only insert fields that actually exist in PostgreSQL
        filtered_record = {
            key: value
            for key, value in record.items()
            if key in table_columns
        }

        ignored_fields = set(record) - table_columns

        if ignored_fields:
            print(
                f"[WARN] {table_name} record {index}: "
                f"ignored fields {sorted(ignored_fields)}"
            )

        if not filtered_record:
            print(
                f"[ERROR] {table_name} record {index}: "
                "no matching database columns"
            )
            continue

        columns = list(filtered_record.keys())

        values = [
            adapt_value(filtered_record[column])
            for column in columns
        ]

        query = sql.SQL("""
            INSERT INTO {table} ({columns})
            VALUES ({placeholders})
        """).format(

            table=sql.Identifier(table_name),

            columns=sql.SQL(", ").join(
                sql.Identifier(column)
                for column in columns
            ),

            placeholders=sql.SQL(", ").join(
                sql.Placeholder()
                for _ in columns
            ),
        )

        try:
            with conn.cursor() as cur:
                cur.execute(query, values)

            inserted += 1

        except Exception as exc:

            print(
                f"\n[FAIL] {table_name} "
                f"record #{index}"
            )

            print(record)
            print(f"Reason: {exc}")

            raise

    print(
        f"[PASS] {table_name}: "
        f"{inserted}/{len(records)} records inserted"
    )


def main():

    print("=" * 70)
    print("TT&T OPERATIONAL DATA LOADER")
    print("=" * 70)

    with psycopg.connect(**DB_CONFIG) as conn:

        print(
            f"\nConnected to database: "
            f"{DB_CONFIG['dbname']}\n"
        )

        try:

            for filename, table_name in LOAD_ORDER:

                path = OPERATIONAL_DIR / filename

                if not path.exists():
                    print(
                        f"[SKIP] File not found: {filename}"
                    )
                    continue

                records = load_json(path)

                print(
                    f"\nLoading {filename} "
                    f"→ {table_name}"
                )

                insert_records(
                    conn,
                    table_name,
                    records,
                )

            # Commit EVERYTHING only if all inserts succeed
            conn.commit()

        except Exception:

            print(
                "\nERROR encountered."
                "\nRolling back database load..."
            )

            conn.rollback()

            raise

    print("\n" + "=" * 70)
    print("DATA LOAD COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()