from __future__ import annotations

from fastmcp import Client

from packages.mcp_server.server import mcp


async def call_invoice_comparison(
    account_id: str,
) -> dict:
    """
    Call the TT&T invoice_comparison MCP tool.

    account_id must come from trusted session context,
    not from the language model.
    """

    async with Client(mcp) as client:

        result = await client.call_tool(
            "invoice_comparison",
            {
                "account_id": account_id,
            },
        )

    if result.is_error:
        raise RuntimeError(
            "invoice_comparison MCP tool failed."
        )

    if result.structured_content is None:
        raise RuntimeError(
            "MCP tool returned no structured content."
        )

    return result.structured_content


async def call_outage_lookup(
    postal_code: str,
    include_resolved: bool = False,
) -> dict:
    """
    Call the TT&T outage_lookup MCP tool.
    """

    async with Client(mcp) as client:

        result = await client.call_tool(
            "outage_lookup",
            {
                "postal_code": postal_code,
                "include_resolved": include_resolved,
            },
        )

    if result.is_error:
        raise RuntimeError(
            "outage_lookup MCP tool failed."
        )

    if result.structured_content is None:
        raise RuntimeError(
            "MCP outage tool returned no structured content."
        )

    return result.structured_content


async def call_create_support_ticket(
    account_id: str,
    category: str,
    summary: str,
    idempotency_key: str,
    line_id: str | None = None,
) -> dict:
    """
    Call the TT&T support_ticket_create MCP tool.
    """

    async with Client(mcp) as client:

        result = await client.call_tool(
            "support_ticket_create",
            {
                "account_id": account_id,
                "category": category,
                "summary": summary,
                "idempotency_key": idempotency_key,
                "line_id": line_id,
            },
        )

    if result.is_error:
        raise RuntimeError(
            "support_ticket_create MCP tool failed."
        )

    if result.structured_content is None:
        raise RuntimeError(
            "MCP ticket tool returned no structured content."
        )

    return result.structured_content