from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from packages.mcp_server.db import get_connection


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DEMO_SESSIONS_PATH = (
    ROOT
    / "data"
    / "config"
    / "demo_sessions.json"
)


# ============================================================
# SESSION CONTEXT MODEL
# ============================================================

@dataclass
class SessionContext:
    """
    Trusted runtime identity/context derived from a demo session.

    The customer message and the LLM must not be allowed
    to replace these values.
    """

    session_id: str
    principal_id: str
    user_id: str
    display_name: str

    account_id: str
    account_status: str

    postal_code: str
    service_area: str

    line_ids: list[str]


# ============================================================
# LOAD DEMO SESSION FIXTURE
# ============================================================

def load_demo_sessions() -> list[dict]:
    """
    Load test-harness session mappings.

    These fixture IDs simulate authenticated sessions.
    They are not real authentication tokens.
    """

    with open(
        DEMO_SESSIONS_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    return data["sessions"]


def find_session_fixture(
    session_id: str,
) -> dict:
    """
    Find the configured fixture for a session ID.
    """

    sessions = load_demo_sessions()

    for session in sessions:

        if (
            session["session_fixture_id"]
            == session_id
        ):
            return session

    raise ValueError(
        "Invalid or unknown session."
    )


# ============================================================
# DATABASE VERIFICATION
# ============================================================

def resolve_session(
    session_id: str,
) -> SessionContext:
    """
    Resolve a demo session into trusted customer context.

    The mapping from demo_sessions.json is verified against
    PostgreSQL before being accepted.

    This prevents downstream tools from trusting arbitrary
    account IDs supplied in a customer message.
    """

    if not session_id:
        raise ValueError(
            "session_id is required."
        )

    fixture = find_session_fixture(
        session_id
    )

    principal_id = fixture[
        "principal_id"
    ]

    expected_user_id = fixture[
        "user_id"
    ]

    expected_account_id = fixture[
        "account_id"
    ]


    # --------------------------------------------------------
    # Verify principal -> user -> account relationship
    # --------------------------------------------------------

    identity_sql = """
        SELECT
            u.user_id,
            u.principal_id,
            u.display_name,
            a.account_id,
            a.status,
            a.postal_code,
            a.service_area

        FROM users u

        JOIN accounts a
          ON a.user_id = u.user_id

        WHERE u.principal_id = %s
          AND u.user_id = %s
          AND a.account_id = %s;
    """


    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                identity_sql,
                (
                    principal_id,
                    expected_user_id,
                    expected_account_id,
                ),
            )

            identity = cur.fetchone()


    if identity is None:

        raise PermissionError(
            "Session identity could not be "
            "verified against operational data."
        )


    (
        user_id,
        verified_principal_id,
        display_name,
        account_id,
        account_status,
        postal_code,
        service_area,
    ) = identity


    # --------------------------------------------------------
    # Retrieve lines belonging ONLY to this account
    # --------------------------------------------------------

    lines_sql = """
        SELECT line_id

        FROM lines

        WHERE account_id = %s

        ORDER BY line_id;
    """


    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                lines_sql,
                (account_id,),
            )

            rows = cur.fetchall()


    line_ids = [
        row[0]
        for row in rows
    ]


    return SessionContext(
        session_id=session_id,
        principal_id=verified_principal_id,
        user_id=user_id,
        display_name=display_name,
        account_id=account_id,
        account_status=account_status,
        postal_code=postal_code,
        service_area=service_area,
        line_ids=line_ids,
    )