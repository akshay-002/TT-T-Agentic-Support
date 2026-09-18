from __future__ import annotations
from typing import Any
import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.mcp_server.ticket_tools import (
    create_support_ticket,
)


# ============================================================
# IMPORTS
# ============================================================

from mcp.server import MCPServer

from packages.mcp_server.invoice_tools import (
    get_invoice_comparison,
)

from packages.mcp_server.outage_tools import (
    get_outages,
)



# ============================================================
# MCP SERVER
# ============================================================

mcp = MCPServer(
    "TT&T Customer Service Tools"
)


# ============================================================
# TOOL: INVOICE COMPARISON
# ============================================================

@mcp.tool(structured_output=True)
def invoice_comparison(
    account_id: str,
) -> dict[str, Any]:

    return get_invoice_comparison(
        account_id=account_id
    )



# ============================================================
# TOOL: # outage_lookup
# ============================================================


@mcp.tool(structured_output=True)
def outage_lookup(
    postal_code: str,
    include_resolved: bool = False,
) -> dict[str, Any]:
    """
    Retrieve TT&T outage information for a postal code.

    Use this when a customer asks whether service is down,
    whether there is an outage in their area, or whether
    TT&T is investigating a network issue.

    Returns authoritative outage facts from the
    operational database.
    """

    return get_outages(
        postal_code=postal_code,
        include_resolved=include_resolved,
    )

# ============================================================
# TOOL: # support_ticket
# ============================================================

@mcp.tool(structured_output=True)
def support_ticket_create(
    account_id: str,
    category: str,
    summary: str,
    idempotency_key: str,
    line_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a TT&T support ticket.

    Use this only when the customer explicitly asks to open,
    create, submit, or file a support ticket or review request.

    This tool performs a WRITE operation in PostgreSQL.

    Idempotency protection prevents duplicate tickets when
    the same request is retried.
    """

    return create_support_ticket(
        account_id=account_id,
        category=category,
        summary=summary,
        idempotency_key=idempotency_key,
        line_id=line_id,
    )