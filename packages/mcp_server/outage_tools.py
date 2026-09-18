from __future__ import annotations

from packages.mcp_server.db import get_connection


def get_outages(
    postal_code: str,
    include_resolved: bool = False,
) -> dict:
    """
    Retrieve TT&T outage information for a postal code.

    Args:
        postal_code:
            Customer/service-location postal code.

        include_resolved:
            If False, return only active or investigating outages.
            If True, resolved outages are included too.

    Returns:
        Structured operational outage information from PostgreSQL.
    """

    if not postal_code:
        raise ValueError(
            "postal_code is required."
        )

    postal_code = postal_code.strip()

    # --------------------------------------------------------
    # Query operational outage records
    # --------------------------------------------------------

    if include_resolved:

        sql = """
            SELECT
                outage_id,
                service_area,
                postal_code,
                network_type,
                status,
                started_at,
                observed_at,
                estimated_resolution,
                resolved_at,
                summary
            FROM outages
            WHERE postal_code = %s
            ORDER BY started_at DESC;
        """

        params = (postal_code,)

    else:

        sql = """
            SELECT
                outage_id,
                service_area,
                postal_code,
                network_type,
                status,
                started_at,
                observed_at,
                estimated_resolution,
                resolved_at,
                summary
            FROM outages
            WHERE postal_code = %s
              AND status IN ('active', 'investigating')
            ORDER BY started_at DESC;
        """

        params = (postal_code,)


    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                sql,
                params,
            )

            rows = cur.fetchall()


    columns = [
        "outage_id",
        "service_area",
        "postal_code",
        "network_type",
        "status",
        "started_at",
        "observed_at",
        "estimated_resolution",
        "resolved_at",
        "summary",
    ]


    outages = [
        dict(zip(columns, row))
        for row in rows
    ]


    # --------------------------------------------------------
    # Build useful summary flags for the agent
    # --------------------------------------------------------

    active_outages = [
        outage
        for outage in outages
        if outage["status"] == "active"
    ]

    investigating_outages = [
        outage
        for outage in outages
        if outage["status"] == "investigating"
    ]

    resolved_outages = [
        outage
        for outage in outages
        if outage["status"] == "resolved"
    ]


    return {
        "postal_code": postal_code,

        "outage_found": bool(outages),

        "active_outage_found": bool(
            active_outages
        ),

        "investigation_found": bool(
            investigating_outages
        ),

        "outage_count": len(outages),

        "outages": outages,

        "status_counts": {
            "active": len(active_outages),
            "investigating": len(
                investigating_outages
            ),
            "resolved": len(
                resolved_outages
            ),
        },
    }