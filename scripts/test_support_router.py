from __future__ import annotations

import asyncio

from packages.router.support_router import (
    route_question,
)

from packages.support_service import (
    answer_customer_question,
)


async def run_test(
    session_id: str,
    question: str,
    request_id: str | None = None,
):
    route = route_question(
        question
    )

    print("=" * 80)
    print("TT&T AUTOMATIC SUPPORT ROUTER TEST")
    print("=" * 80)

    print()
    print(f"Session : {session_id}")
    print(f"Question: {question}")
    print(f"Route   : {route}")

    answer = await answer_customer_question(
        question=question,
        session_id=session_id,
        request_id=request_id,
    )

    print()
    print("=" * 80)
    print("CUSTOMER ANSWER")
    print("=" * 80)
    print()
    print(answer)


async def main():
    await run_test(
        session_id="SESSION_01",
        request_id="AUTH_TEST_003",
        question=(
            "Please open a support ticket "
            "for LINE_2001 about my service."
        ),
    )

if __name__ == "__main__":
    asyncio.run(main())