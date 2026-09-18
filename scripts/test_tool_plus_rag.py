from __future__ import annotations

import json

from packages.mcp_server.invoice_tools import (
    get_invoice_comparison,
)

from packages.mcp_server.policy_tools import (
    get_policy_chunks,
)


def main():

    account_id = "ACC_1001"

    print("=" * 80)
    print("TT&T OPERATIONAL TOOL + RAG TEST")
    print("=" * 80)

    # --------------------------------------------------------
    # 1. Get customer-specific billing facts
    # --------------------------------------------------------

    comparison = get_invoice_comparison(
        account_id
    )

    print("\nOPERATIONAL FACTS\n")

    print(
        json.dumps(
            comparison,
            indent=2,
        )
    )

    # --------------------------------------------------------
    # 2. Extract policies associated with actual changes
    # --------------------------------------------------------

    policy_ids = comparison[
        "changed_policy_ids"
    ]

    print("\nPOLICIES NEEDED")
    print(policy_ids)

    # --------------------------------------------------------
    # 3. Retrieve exact RAG evidence
    # --------------------------------------------------------

    chunks = get_policy_chunks(
        policy_ids
    )

    print("\nRAG EVIDENCE\n")

    for chunk in chunks:

        print("-" * 80)

        print(
            f"Document : "
            f"{chunk['document_id']}"
        )

        print(
            f"Title    : "
            f"{chunk['title']}"
        )

        print(
            f"Section  : "
            f"{chunk['section_title']}"
        )

        print()

        print(
            chunk["content"]
        )

        print()


if __name__ == "__main__":
    main()