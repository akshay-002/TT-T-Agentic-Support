from packages.mcp_server.invoice_tools import (
    get_invoice_comparison,
)

from packages.mcp_server.policy_tools import (
    get_policy_chunks,
)

from packages.llm.grounded_answer import (
    generate_grounded_answer,
)


def run_test(
    account_id: str,
    question: str,
):

    print("=" * 80)
    print("TT&T GROUNDED ANSWER TEST")
    print("=" * 80)

    print(f"\nAccount : {account_id}")
    print(f"Question: {question}")

    # 1. Get customer-specific operational facts
    comparison = get_invoice_comparison(
        account_id
    )

    # 2. Determine which policies explain actual bill changes
    policy_ids = comparison[
        "changed_policy_ids"
    ]

    print(
        f"\nDetected policies: {policy_ids}"
    )

    # 3. Retrieve supporting policy chunks
    policy_chunks = get_policy_chunks(
        policy_ids=policy_ids,
        limit_per_policy=3,
    )

    print(
        f"Retrieved policy chunks: "
        f"{len(policy_chunks)}"
    )

    # 4. Generate grounded answer
    answer = generate_grounded_answer(
        question=question,
        operational_facts=comparison,
        policy_chunks=policy_chunks,
    )

    print("\n" + "=" * 80)
    print("CUSTOMER ANSWER")
    print("=" * 80)
    print()
    print(answer)
    print()

def main():

    run_test(
        account_id="ACC_1006",
        question=(
            "What caused the extra $10 "
            "on my latest bill?"
        ),
    )


if __name__ == "__main__":
    main()