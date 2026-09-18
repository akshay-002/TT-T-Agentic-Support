from __future__ import annotations

from datetime import datetime, timezone

from packages.mcp_server.db import get_connection


ALLOWED_CATEGORIES = {
    "billing",
    "connectivity",
    "account",
    "device",
    "number_porting",
    "other",
}


def utc_now_iso() -> str:
    """
    Return the current UTC time in ISO-8601 format.
    """

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def get_next_ticket_id() -> str:
    """
    Generate the next ticket ID based on existing TKT_#### IDs.

    Example:
        highest existing = TKT_7010
        next             = TKT_7011
    """

    sql = """
        SELECT ticket_id
        FROM support_tickets
        WHERE ticket_id LIKE 'TKT_%'
        ORDER BY ticket_id DESC
        LIMIT 1;
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql)

            row = cur.fetchone()

    if not row:
        return "TKT_7001"

    latest_ticket_id = row[0]

    number = int(
        latest_ticket_id.split("_")[1]
    )

    return f"TKT_{number + 1:04d}"


def validate_account(
    account_id: str,
) -> None:
    """
    Confirm that the account exists.
    """

    sql = """
        SELECT 1
        FROM accounts
        WHERE account_id = %s;
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                sql,
                (account_id,),
            )

            row = cur.fetchone()

    if row is None:
        raise ValueError(
            f"Unknown account_id: {account_id}"
        )


def validate_line(
    account_id: str,
    line_id: str | None,
) -> None:
    """
    If line_id is supplied, confirm that:
    1. the line exists
    2. it belongs to the supplied account
    """

    if line_id is None:
        return

    sql = """
        SELECT 1
        FROM lines
        WHERE line_id = %s
          AND account_id = %s;
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                sql,
                (
                    line_id,
                    account_id,
                ),
            )

            row = cur.fetchone()

    if row is None:
        raise ValueError(
            f"Line {line_id} does not belong "
            f"to account {account_id}."
        )


def create_support_ticket(
    account_id: str,
    category: str,
    summary: str,
    idempotency_key: str,
    line_id: str | None = None,
) -> dict:
    """
    Create a TT&T support ticket.

    This is a WRITE operation.

    Idempotency protection ensures that retrying the
    same request does not create duplicate tickets.
    """

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if not account_id:
        raise ValueError(
            "account_id is required."
        )

    if not summary or not summary.strip():
        raise ValueError(
            "summary is required."
        )

    if not idempotency_key:
        raise ValueError(
            "idempotency_key is required."
        )

    category = category.strip().lower()

    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Unsupported ticket category: {category}"
        )

    validate_account(
        account_id
    )

    validate_line(
        account_id=account_id,
        line_id=line_id,
    )


    # --------------------------------------------------------
    # Check idempotency first
    # --------------------------------------------------------

    existing_sql = """
        SELECT
            ticket_id,
            account_id,
            line_id,
            category,
            summary,
            status,
            created_at,
            updated_at,
            resolved_at,
            idempotency_key
        FROM support_tickets
        WHERE idempotency_key = %s;
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                existing_sql,
                (idempotency_key,),
            )

            existing = cur.fetchone()

    if existing:

        columns = [
            "ticket_id",
            "account_id",
            "line_id",
            "category",
            "summary",
            "status",
            "created_at",
            "updated_at",
            "resolved_at",
            "idempotency_key",
        ]

        result = dict(
            zip(columns, existing)
        )

        result["created_new"] = False

        return result


    # --------------------------------------------------------
    # Create ticket
    # --------------------------------------------------------

    ticket_id = get_next_ticket_id()

    now = utc_now_iso()

    status = "open"


    insert_sql = """
        INSERT INTO support_tickets (
            ticket_id,
            account_id,
            line_id,
            category,
            summary,
            status,
            created_at,
            updated_at,
            resolved_at,
            idempotency_key
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            NULL,
            %s
        )
        RETURNING
            ticket_id,
            account_id,
            line_id,
            category,
            summary,
            status,
            created_at,
            updated_at,
            resolved_at,
            idempotency_key;
    """


    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                insert_sql,
                (
                    ticket_id,
                    account_id,
                    line_id,
                    category,
                    summary.strip(),
                    status,
                    now,
                    now,
                    idempotency_key,
                ),
            )

            row = cur.fetchone()

        conn.commit()


    columns = [
        "ticket_id",
        "account_id",
        "line_id",
        "category",
        "summary",
        "status",
        "created_at",
        "updated_at",
        "resolved_at",
        "idempotency_key",
    ]

    result = dict(
        zip(columns, row)
    )

    result["created_new"] = True

    return result