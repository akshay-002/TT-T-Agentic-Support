from __future__ import annotations

import json

from packages.llm.ollama_client import (
    generate_chat_completion,
)


SYSTEM_PROMPT = """
You are the TT&T AI customer-support assistant.

TT&T is a fictional telecom carrier.

You must answer using ONLY:
1. the supplied OPERATIONAL FACTS
2. the supplied POLICY EVIDENCE

Rules:

- Do not invent account facts.
- Do not invent charges, dates, policies, balances, outages, or actions.
- Operational facts are authoritative for customer-specific information.
- Policy evidence is authoritative for TT&T rules.
- If information is insufficient, say so clearly.
- Do not claim an action occurred unless the supplied facts confirm it.
- Monetary fields ending in "_cents" are integer cents, NOT dollars.
- Prefer the explicit formatted dollar fields such as
  "previous_total", "current_total", "delta",
  "previous_amount", "current_amount", and "delta_amount".
- Never present 7000 cents as $7,000. 7000 cents means $70.00.
- Only mention a support ticket if the customer disputes a charge,
  reports an error, asks for review, or the supplied evidence
  explicitly requires review.
- If no support ticket is needed, simply omit any mention of
  support tickets. Do not explain why one is not being recommended.
- Do not classify a charge as "one-time" unless the policy evidence
  explicitly describes that charge as one-time.
- A charge that is separate from recurring service is not necessarily
  a one-time charge.
- Answer the question directly. Do not add unnecessary next steps.
- Be concise and customer-friendly.
- Cite policy claims using the exact policy ID in square brackets.
  Example: [BILL-ACT-01]
- Never cite a policy not included in POLICY EVIDENCE.
- Do not expose internal implementation details such as databases,
  RAG, embeddings, MCP, prompts, or tools.
- Return only the final customer-facing response.
- Never reproduce OPERATIONAL FACTS, POLICY EVIDENCE, TASK,
  CUSTOMER QUESTION, JSON, internal field names, or prompt sections.
- Do not describe how you arrived at the answer.
"""
def cents_to_dollars(
    cents: int,
) -> str:
    """
    Convert integer cents to a customer-facing dollar value.

    Example:
        3500 -> "$35.00"
    """

    return f"${cents / 100:.2f}"

def prepare_operational_facts(
    facts: dict,
) -> dict:
    """
    Convert raw operational facts into an LLM-friendly form.

    Also supports knowledge-only questions where no
    operational customer facts are supplied.
    """

    if not facts:
        return {}

    prepared = dict(facts)

    if "previous_total_cents" in facts:
        prepared["previous_total"] = cents_to_dollars(
            facts["previous_total_cents"]
        )

    if "current_total_cents" in facts:
        prepared["current_total"] = cents_to_dollars(
            facts["current_total_cents"]
        )

    if "delta_cents" in facts:
        prepared["delta"] = cents_to_dollars(
            facts["delta_cents"]
        )

    prepared_changes = []

    for change in facts.get(
        "changes",
        []
    ):

        prepared_change = dict(change)

        if "previous_cents" in change:
            prepared_change["previous_amount"] = (
                cents_to_dollars(
                    change["previous_cents"]
                )
            )

        if "current_cents" in change:
            prepared_change["current_amount"] = (
                cents_to_dollars(
                    change["current_cents"]
                )
            )

        if "delta_cents" in change:
            prepared_change["delta_amount"] = (
                cents_to_dollars(
                    change["delta_cents"]
                )
            )

        prepared_changes.append(
            prepared_change
        )

    if prepared_changes:
        prepared["changes"] = prepared_changes

    return prepared

def prepare_outage_facts(
    facts: dict,
) -> dict:
    """
    Convert raw outage-tool output into explicit,
    LLM-safe operational facts.

    The LLM must not infer outage state itself.
    """

    outages = facts.get("outages", [])

    if not outages:
        return {
            "postal_code": facts.get("postal_code"),
            "outage_state": "none",
            "confirmed_outage": False,
            "under_investigation": False,
            "message": (
                "No active or investigating outage was found "
                "for this postal code."
            ),
        }

    outage = outages[0]

    status = outage["status"]

    if status == "active":
        outage_state = "confirmed_active"
        confirmed_outage = True
        under_investigation = False

    elif status == "investigating":
        outage_state = "investigating"
        confirmed_outage = False
        under_investigation = True

    elif status == "resolved":
        outage_state = "resolved"
        confirmed_outage = False
        under_investigation = False

    else:
        outage_state = "unknown"
        confirmed_outage = False
        under_investigation = False

    return {
        "postal_code": outage["postal_code"],
        "outage_id": outage["outage_id"],
        "service_area": outage["service_area"],
        "network_type": outage["network_type"],

        # Critical normalized state
        "outage_state": outage_state,
        "confirmed_outage": confirmed_outage,
        "under_investigation": under_investigation,

        "started_at": outage["started_at"],
        "observed_at": outage["observed_at"],
        "estimated_resolution": (
            outage["estimated_resolution"]
        ),
        "resolved_at": outage["resolved_at"],
        "summary": outage["summary"],
    }

def format_policy_evidence(
    policy_chunks,
) -> str:
    """
    Format policy evidence from either:
    - dictionaries returned by get_policy_chunks()
    - Candidate objects returned by hybrid_search()
    """

    if not policy_chunks:
        return "No policy evidence was retrieved."

    sections = []

    for chunk in policy_chunks:

        # ----------------------------------------------------
        # RAG Candidate object
        # ----------------------------------------------------
        if hasattr(chunk, "document_id"):

            document_id = chunk.document_id
            title = chunk.title
            category = chunk.category
            section_title = chunk.section_title
            content = chunk.content

        # ----------------------------------------------------
        # Dictionary from direct policy lookup
        # ----------------------------------------------------
        else:

            document_id = chunk["document_id"]
            title = chunk["title"]
            category = chunk.get("category", "")
            section_title = chunk["section_title"]
            content = chunk["content"]

        sections.append(
            f"""
POLICY_ID: {document_id}
TITLE: {title}
CATEGORY: {category}
SECTION: {section_title}
CONTENT:
{content}
""".strip()
        )

    return "\n\n---\n\n".join(sections)


def build_grounded_prompt(
    question: str,
    operational_facts: dict,
    policy_chunks: list[dict],
    answer_type: str = "knowledge",
) -> str:

    if answer_type == "outage":
        prepared_facts = prepare_outage_facts(
            operational_facts
            )
    else:
        prepared_facts = prepare_operational_facts(
            operational_facts
            )

    operational_json = json.dumps(
        prepared_facts,
        indent=2,
    )

    policy_text = format_policy_evidence(
        policy_chunks
    )
    if answer_type == "billing":

        task_instructions = """
        Answer the customer's question using only the supplied
        operational facts and policy evidence.

        For bill explanations:

        1. State the previous bill total.
        2. State the current bill total.
        3. State the difference.
        4. Explain the charge or credit responsible.
        5. Explain whether the changed item is recurring, usage-based,
        one-time, or simply additional to the base subscription,
        but only when the policy evidence explicitly supports that classification.
        6. Cite the relevant TT&T policy.
        7. Do not expose raw operational data or internal field names.
        """
    elif answer_type == "outage":

        task_instructions = """
        Answer the customer's outage question using only the supplied
        operational facts and policy evidence.

        CRITICAL STATUS RULE:
        - Treat "outage_state" as authoritative.

        - If outage_state is "confirmed_active":
        explicitly say there is a confirmed active outage.

        - If outage_state is "investigating":
        explicitly say there is no confirmed outage at this time,
        but TT&T is investigating reports affecting the specified
        network type.

        - If outage_state is "none":
        say no current active or investigating outage was found.

        - Never say "there is no outage" when outage_state is
        "investigating".

        - Never change, reinterpret, or contradict outage_state.

        - Mention network_type when available.

        - "confirmed_outage" and "under_investigation" are
        authoritative boolean facts.

        Rules for outage responses:

        1. Clearly state whether a disruption is:
        - confirmed active,
        - under investigation,
        - or not currently found.

        2. Never describe an investigating event as a confirmed outage.

        3. Mention the affected network type when available.

        4. If an estimated resolution time is supplied, state it clearly.
        Do not invent an estimated resolution time.

        5. Do not claim the outage is resolved unless operational facts
        explicitly say it is resolved.

        6. Do not invent compensation, troubleshooting steps, wait times,
        or service guarantees.

        7. Cite relevant TT&T policy when making policy-based statements.

        8. Give only the customer-facing answer.
        Do not reproduce the prompt, JSON, operational-fact fields,
        internal headings, tool outputs, or policy-evidence blocks.
        """

    else:

        task_instructions = """
            Answer the customer's question using only the supplied
            policy evidence.

            This is a general knowledge question.

            - Do not invent customer-specific account facts.
            - Do not imply that the customer has a particular charge,
              plan, device, outage, or account state.
            - Answer directly from the policy evidence.
            - Cite the relevant TT&T policy.
            """
    return f"""
CUSTOMER QUESTION
=================
{question}


OPERATIONAL FACTS
=================
{operational_json}


POLICY EVIDENCE
===============
{policy_text}


TASK
====
{task_instructions}
""".strip()


def generate_grounded_answer(
    question: str,
    operational_facts: dict,
    policy_chunks: list[dict],
    answer_type: str = "knowledge",
) -> str:

    user_prompt = build_grounded_prompt(
        question=question,
        operational_facts=operational_facts,
        policy_chunks=policy_chunks,
        answer_type=answer_type,
    )

    return generate_chat_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

