from __future__ import annotations

from packages.mcp_server.db import get_connection


def get_policy_chunks(
    policy_ids: list[str],
    limit_per_policy: int = 3,
) -> list[dict]:
    """
    Retrieve RAG chunks directly for known policy IDs.

    Used when an operational tool has already identified
    which company policies explain the account facts.
    """

    if not policy_ids:
        return []

    results = []

    with get_connection() as conn:

        with conn.cursor() as cur:

            for policy_id in policy_ids:

                cur.execute(
                    """
                    SELECT
                        c.chunk_id,
                        c.document_id,
                        d.title,
                        d.category,
                        c.section_title,
                        c.content

                    FROM chunks c

                    JOIN documents d
                      ON d.document_id = c.document_id
                     AND d.version = c.document_version

                    WHERE c.document_id = %s

                    ORDER BY c.chunk_index

                    LIMIT %s;
                    """,
                    (
                        policy_id,
                        limit_per_policy,
                    ),
                )

                rows = cur.fetchall()

                for row in rows:

                    (
                        chunk_id,
                        document_id,
                        title,
                        category,
                        section_title,
                        content,
                    ) = row

                    results.append(
                        {
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "title": title,
                            "category": category,
                            "section_title": section_title,
                            "content": content,
                        }
                    )

    return results