from __future__ import annotations


def is_billing_question(
    question: str,
) -> bool:
    """
    Determine whether the customer is asking about
    their bill or invoice.

    This is deterministic routing v1.
    """

    text = question.lower().strip()

    billing_terms = [
        "bill",
        "billing",
        "invoice",
        "charged",
        "charge",
        "charges",
        "payment due",
        "bill higher",
        "bill lower",
        "extra charge",
        "extra fee",
    ]

    return any(
        term in text
        for term in billing_terms
    )


def route_question(
    question: str,
) -> str:
    if is_ticket_creation_request(question):
        return "support_ticket"

    if is_billing_question(question):
        return "billing"

    if is_outage_question(question):
        return "outage"

    return "knowledge"


def is_outage_question(
    question: str,
) -> bool:
    """
    Detect outage or service-disruption questions.
    """

    text = question.lower().strip()

    outage_terms = [
        "outage",
        "service down",
        "network down",
        "no service",
        "service unavailable",
        "network issue",
        "network problem",
        "5g down",
        "lte down",
        "can't connect",
        "cannot connect",
        "service disruption",
    ]

    return any(
        term in text
        for term in outage_terms
    )


def is_ticket_creation_request(
    question: str,
) -> bool:
    """
    Detect explicit requests to create/open/file a support ticket.
    """

    text = question.lower().strip()

    explicit_ticket_phrases = [
        "open a ticket",
        "create a ticket",
        "file a ticket",
        "submit a ticket",
        "open a support ticket",
        "create a support ticket",
        "file a support ticket",
        "submit a support ticket",
        "open a case",
        "create a case",
        "submit a case",
        "request a review",
        "open a review",
    ]

    return any(
        phrase in text
        for phrase in explicit_ticket_phrases
    )