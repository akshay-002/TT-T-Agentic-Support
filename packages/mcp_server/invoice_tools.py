from __future__ import annotations

from collections import defaultdict

from packages.mcp_server.db import get_connection


# ============================================================
# GET TWO MOST RECENT INVOICES
# ============================================================

def get_two_latest_invoices(
    account_id: str,
) -> list[dict]:

    """
    Retrieve the two most recent invoices for an account.

    Returns them oldest -> newest so that:

        invoices[0] = previous
        invoices[1] = current
    """

    sql = """
        SELECT
            invoice_id,
            account_id,
            period_start,
            period_end,
            issued_at,
            due_date,
            currency,
            total_cents,
            amount_paid_cents,
            balance_due_cents,
            status

        FROM invoices

        WHERE account_id = %s

        ORDER BY issued_at DESC

        LIMIT 2;
    """


    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                sql,
                (account_id,),
            )

            rows = cur.fetchall()


    if len(rows) < 2:

        raise ValueError(
            f"Account {account_id} does not have "
            f"at least two invoices."
        )


    columns = [
        "invoice_id",
        "account_id",
        "period_start",
        "period_end",
        "issued_at",
        "due_date",
        "currency",
        "total_cents",
        "amount_paid_cents",
        "balance_due_cents",
        "status",
    ]


    invoices = [
        dict(zip(columns, row))
        for row in rows
    ]


    # Query returned newest -> oldest.
    # Reverse so result becomes previous -> current.

    invoices.reverse()


    return invoices


# ============================================================
# GET INVOICE ITEMS
# ============================================================

def get_invoice_items(
    invoice_ids: list[str],
) -> list[dict]:

    """
    Retrieve all line items associated with the supplied invoices.
    """

    sql = """
        SELECT
            item_id,
            invoice_id,
            line_id,
            item_type,
            description,
            amount_cents,
            policy_id,
            service_event_id

        FROM invoice_items

        WHERE invoice_id = ANY(%s)

        ORDER BY
            invoice_id,
            item_id;
    """


    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                sql,
                (invoice_ids,),
            )

            rows = cur.fetchall()


    columns = [
        "item_id",
        "invoice_id",
        "line_id",
        "item_type",
        "description",
        "amount_cents",
        "policy_id",
        "service_event_id",
    ]


    return [
        dict(zip(columns, row))
        for row in rows
    ]


# ============================================================
# AGGREGATE ITEM TYPES
# ============================================================

def aggregate_items(
    items: list[dict],
    invoice_id: str,
) -> dict[str, int]:

    """
    Aggregate invoice-item amounts by item_type.

    Example:

        {
            "plan_charge": 7000,
            "activation_fee": 3500,
            "tax": 0
        }
    """

    totals = defaultdict(int)


    for item in items:

        if item["invoice_id"] != invoice_id:
            continue


        totals[
            item["item_type"]
        ] += item["amount_cents"]


    return dict(totals)


# ============================================================
# BUILD ITEM-TYPE CHANGES
# ============================================================

def build_changes(
    previous_invoice_id: str,
    current_invoice_id: str,
    items: list[dict],
) -> list[dict]:

    """
    Compare item categories across the two invoices.
    """

    previous_totals = aggregate_items(
        items,
        previous_invoice_id,
    )

    current_totals = aggregate_items(
        items,
        current_invoice_id,
    )


    item_types = sorted(
        set(previous_totals)
        |
        set(current_totals)
    )


    changes = []


    for item_type in item_types:

        previous_cents = previous_totals.get(
            item_type,
            0,
        )

        current_cents = current_totals.get(
            item_type,
            0,
        )

        delta_cents = (
            current_cents
            - previous_cents
        )


        # Find policies related to this item type.

        policy_ids = sorted(
            {
                item["policy_id"]

                for item in items

                if item["item_type"] == item_type
                and item.get("policy_id")
            }
        )


        # Find source item IDs.

        source_item_ids = [
            item["item_id"]

            for item in items

            if item["item_type"] == item_type
        ]


        changes.append(
            {
                "item_type": item_type,

                "previous_cents":
                    previous_cents,

                "current_cents":
                    current_cents,

                "delta_cents":
                    delta_cents,

                "policy_ids":
                    policy_ids,

                "source_item_ids":
                    source_item_ids,
            }
        )


    return changes


# ============================================================
# PUBLIC TOOL FUNCTION
# ============================================================

def get_invoice_comparison(
    account_id: str,
) -> dict:

    """
    Compare the latest two invoices for an account.

    This is the business-logic function that will later
    be exposed through MCP.

    It does NOT use an LLM.

    All returned account facts come directly from PostgreSQL.
    """

    if not account_id:

        raise ValueError(
            "account_id is required."
        )


    # --------------------------------------------------------
    # 1. GET TWO MOST RECENT INVOICES
    # --------------------------------------------------------

    invoices = get_two_latest_invoices(
        account_id
    )


    previous_invoice = invoices[0]
    current_invoice = invoices[1]


    # --------------------------------------------------------
    # 2. GET BOTH INVOICES' ITEMS
    # --------------------------------------------------------

    invoice_ids = [
        previous_invoice["invoice_id"],
        current_invoice["invoice_id"],
    ]


    items = get_invoice_items(
        invoice_ids
    )


    # --------------------------------------------------------
    # 3. COMPARE LINE ITEM TYPES
    # --------------------------------------------------------

    changes = build_changes(
        previous_invoice_id=(
            previous_invoice["invoice_id"]
        ),

        current_invoice_id=(
            current_invoice["invoice_id"]
        ),

        items=items,
    )


    # --------------------------------------------------------
    # 4. TOTAL BILL DIFFERENCE
    # --------------------------------------------------------

    delta_cents = (
        current_invoice["total_cents"]
        - previous_invoice["total_cents"]
    )


    # --------------------------------------------------------
    # 5. POLICIES RELATED TO ACTUAL CHANGES
    # --------------------------------------------------------

    changed_policy_ids = sorted(
        {
            policy_id

            for change in changes

            if change["delta_cents"] != 0

            for policy_id in change[
                "policy_ids"
            ]
        }
    )


    # --------------------------------------------------------
    # 6. ALL SOURCE ITEMS
    # --------------------------------------------------------

    source_item_ids = [
        item["item_id"]
        for item in items
    ]


    # --------------------------------------------------------
    # 7. RETURN STRUCTURED TOOL RESULT
    # --------------------------------------------------------

    return {
        "account_id":
            account_id,

        "previous_invoice_id":
            previous_invoice["invoice_id"],

        "current_invoice_id":
            current_invoice["invoice_id"],

        "previous_period": {
            "start":
                previous_invoice["period_start"],

            "end":
                previous_invoice["period_end"],
        },

        "current_period": {
            "start":
                current_invoice["period_start"],

            "end":
                current_invoice["period_end"],
        },

        "previous_total_cents":
            previous_invoice["total_cents"],

        "current_total_cents":
            current_invoice["total_cents"],

        "delta_cents":
            delta_cents,

        "currency":
            current_invoice["currency"],

        "changes":
            changes,

        "changed_policy_ids":
            changed_policy_ids,

        "source_item_ids":
            source_item_ids,
    }