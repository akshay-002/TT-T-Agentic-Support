from __future__ import annotations

import re

from packages.security.session_context import (
    SessionContext,
)


ACCOUNT_ID_PATTERN = re.compile(
    r"\bACC_\d+\b",
    re.IGNORECASE,
)

LINE_ID_PATTERN = re.compile(
    r"\bLINE_\d+\b",
    re.IGNORECASE,
)


def require_account_access(
    context: SessionContext,
    account_id: str,
) -> None:
    """
    Ensure the requested account belongs to the
    authenticated session.
    """

    if account_id.upper() != context.account_id.upper():
        raise PermissionError(
            "Account access is not authorized."
        )


def require_line_access(
    context: SessionContext,
    line_id: str,
) -> None:
    """
    Ensure the requested line belongs to the
    authenticated account.
    """

    authorized_lines = {
        value.upper()
        for value in context.line_ids
    }

    if line_id.upper() not in authorized_lines:
        raise PermissionError(
            "Line access is not authorized."
        )


def resolve_default_line(
    context: SessionContext,
) -> str | None:
    """
    Automatically select a line only when the account
    has exactly one line.

    Never guess between multiple lines.
    """

    if len(context.line_ids) == 1:
        return context.line_ids[0]

    return None


def extract_account_references(
    question: str,
) -> list[str]:
    """
    Find explicit TT&T account IDs in customer text.
    """

    return list(
        dict.fromkeys(
            match.upper()
            for match in ACCOUNT_ID_PATTERN.findall(
                question
            )
        )
    )


def extract_line_references(
    question: str,
) -> list[str]:
    """
    Find explicit TT&T line IDs in customer text.
    """

    return list(
        dict.fromkeys(
            match.upper()
            for match in LINE_ID_PATTERN.findall(
                question
            )
        )
    )


def authorize_question_resources(
    context: SessionContext,
    question: str,
) -> None:
    """
    Validate explicit account or line references found
    in the customer message.

    This runs before routing or tool execution.
    """

    account_references = (
        extract_account_references(
            question
        )
    )

    line_references = (
        extract_line_references(
            question
        )
    )

    for account_id in account_references:
        require_account_access(
            context=context,
            account_id=account_id,
        )

    for line_id in line_references:
        require_line_access(
            context=context,
            line_id=line_id,
        )


def resolve_requested_line(
    context: SessionContext,
    question: str,
) -> str | None:
    """
    Resolve the line to use for an action.

    Rules:
    - If the customer explicitly references exactly one authorized line,
      use that line.
    - If no line is explicitly referenced and the account has exactly
      one line, use the default line.
    - If multiple lines exist and none is explicitly referenced,
      return None.
    """

    line_references = extract_line_references(
        question
    )

    if len(line_references) == 1:
        line_id = line_references[0]

        require_line_access(
            context=context,
            line_id=line_id,
        )

        return line_id

    if len(line_references) > 1:
        raise ValueError(
            "Please specify only one line for this request."
        )

    return resolve_default_line(
        context
    )