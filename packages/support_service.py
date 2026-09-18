from __future__ import annotations

from scripts import hybrid_retrieval as retriever

from packages.mcp_client.client import (
    call_invoice_comparison,
    call_outage_lookup,
    call_create_support_ticket,
)

from packages.mcp_server.policy_tools import (
    get_policy_chunks,
)

from packages.llm.grounded_answer import (
    generate_grounded_answer,
)

from packages.router.support_router import (
    route_question,
)

from packages.security.session_context import (
    resolve_session,
)

from packages.security.authorization import (
    authorize_question_resources,
    resolve_requested_line,
)


retriever.DEBUG = False


def determine_ticket_category(
    question: str,
) -> str:
    """
    Deterministically classify a support-ticket category.
    """

    text = question.lower()

    if any(
        term in text
        for term in [
            "bill",
            "billing",
            "charge",
            "fee",
            "invoice",
            "payment",
        ]
    ):
        return "billing"

    if any(
        term in text
        for term in [
            "outage",
            "network",
            "service",
            "5g",
            "lte",
            "call",
            "calls",
            "data",
            "connect",
            "connection",
        ]
    ):
        return "connectivity"

    if any(
        term in text
        for term in [
            "device",
            "phone",
            "handset",
        ]
    ):
        return "device"

    if any(
        term in text
        for term in [
            "port",
            "transfer number",
            "number transfer",
        ]
    ):
        return "number_porting"

    if any(
        term in text
        for term in [
            "account",
            "profile",
        ]
    ):
        return "account"

    return "other"


def build_ticket_summary(
    question: str,
) -> str:
    """
    Build a deterministic ticket summary from the customer message.
    """

    cleaned = " ".join(
        question.strip().split()
    )

    return cleaned[:500]


def extract_document_id(
    chunk,
) -> str | None:
    """
    Extract a document/policy ID from different chunk representations.

    Supports:
    - dictionaries
    - Candidate-like objects
    - metadata dictionaries
    """

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(chunk, dict):

        for key in [
            "document_id",
            "policy_id",
            "doc_id",
        ]:
            value = chunk.get(key)

            if value:
                return str(value)

        metadata = chunk.get("metadata")

        if isinstance(metadata, dict):
            for key in [
                "document_id",
                "policy_id",
                "doc_id",
            ]:
                value = metadata.get(key)

                if value:
                    return str(value)

        return None

    # --------------------------------------------------------
    # Object attributes
    # --------------------------------------------------------

    for attribute in [
        "document_id",
        "policy_id",
        "doc_id",
    ]:
        value = getattr(
            chunk,
            attribute,
            None,
        )

        if value:
            return str(value)

    metadata = getattr(
        chunk,
        "metadata",
        None,
    )

    if isinstance(metadata, dict):

        for key in [
            "document_id",
            "policy_id",
            "doc_id",
        ]:
            value = metadata.get(key)

            if value:
                return str(value)

    return None


def collect_sources(
    chunks,
) -> list[str]:
    """
    Return unique policy/document IDs from retrieved chunks.
    """

    sources = []

    for chunk in chunks:

        document_id = extract_document_id(
            chunk
        )

        if (
            document_id
            and document_id not in sources
        ):
            sources.append(
                document_id
            )

    return sources


async def answer_customer_question_details(
    question: str,
    session_id: str,
    request_id: str | None = None,
) -> dict:
    """
    Full TT&T customer-support pipeline.

    Returns both:
    - customer-facing answer
    - source document IDs
    """

    # ========================================================
    # 1. SESSION RESOLUTION
    # ========================================================

    context = resolve_session(
        session_id
    )

    # ========================================================
    # 2. AUTHORIZATION
    # ========================================================

    try:
        authorize_question_resources(
            context=context,
            question=question,
        )

    except PermissionError:
        return {
            "answer": (
                "I can only access account and line information "
                "associated with your current session."
            ),
            "sources": [],
        }

    # ========================================================
    # 3. TRUSTED OPERATIONAL CONTEXT
    # ========================================================

    account_id = context.account_id
    postal_code = context.postal_code

    try:
        line_id = resolve_requested_line(
            context=context,
            question=question,
        )

    except ValueError as exc:
        return {
            "answer": str(exc),
            "sources": [],
        }

    # ========================================================
    # 4. ROUTING
    # ========================================================

    route = route_question(
        question
    )

    # ========================================================
    # BILLING
    # ========================================================

    if route == "billing":

        operational_facts = (
            await call_invoice_comparison(
                account_id=account_id
            )
        )

        policy_ids = operational_facts.get(
            "changed_policy_ids",
            [],
        )

        policy_chunks = get_policy_chunks(
            policy_ids=policy_ids,
            limit_per_policy=3,
        )

        answer = generate_grounded_answer(
            question=question,
            operational_facts=operational_facts,
            policy_chunks=policy_chunks,
            answer_type="billing",
        )

        sources = (
            collect_sources(policy_chunks)
            or list(policy_ids)
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    # ========================================================
    # OUTAGE
    # ========================================================

    if route == "outage":

        operational_facts = await call_outage_lookup(
            postal_code=postal_code,
            include_resolved=False,
        )

        policy_chunks = get_policy_chunks(
            policy_ids=["NETWORK-01"],
            limit_per_policy=3,
        )

        answer = generate_grounded_answer(
            question=question,
            operational_facts=operational_facts,
            policy_chunks=policy_chunks,
            answer_type="outage",
        )

        sources = (
            collect_sources(policy_chunks)
            or ["NETWORK-01"]
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    # ========================================================
    # SUPPORT TICKET
    # ========================================================

    if route == "support_ticket":

        if not request_id:
            return {
                "answer": (
                    "I can't safely create the support ticket "
                    "because this request is missing a request identifier."
                ),
                "sources": [],
            }

        category = determine_ticket_category(
            question
        )

        summary = build_ticket_summary(
            question
        )

        idempotency_key = (
            f"SUPPORT_{context.principal_id}_{request_id}"
        )

        ticket = await call_create_support_ticket(
            account_id=account_id,
            line_id=line_id,
            category=category,
            summary=summary,
            idempotency_key=idempotency_key,
        )

        ticket_id = ticket["ticket_id"]
        status = ticket["status"]
        created_new = ticket["created_new"]

        if created_new:
            answer = (
                f"Your support ticket {ticket_id} has been created "
                f"successfully. Its current status is {status}."
            )

        else:
            answer = (
                f"Your support ticket {ticket_id} already exists for "
                f"this request. Its current status is {status}."
            )

        return {
            "answer": answer,
            "sources": [],
        }

    # ========================================================
    # KNOWLEDGE / RAG
    # ========================================================

    if route == "knowledge":

        policy_chunks = retriever.hybrid_search(
            question
        )

        if not policy_chunks:
            return {
                "answer": (
                    "I don't have enough approved TT&T "
                    "information to answer that question."
                ),
                "sources": [],
            }

        answer = generate_grounded_answer(
            question=question,
            operational_facts={},
            policy_chunks=policy_chunks,
            answer_type="knowledge",
        )

        sources = collect_sources(
            policy_chunks
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    raise ValueError(
        f"Unsupported route: {route}"
    )


async def answer_customer_question(
    question: str,
    session_id: str,
    request_id: str | None = None,
) -> str:
    """
    Backward-compatible function.

    Existing tests that expect only a string can continue
    using answer_customer_question().
    """

    result = await answer_customer_question_details(
        question=question,
        session_id=session_id,
        request_id=request_id,
    )

    return result["answer"]