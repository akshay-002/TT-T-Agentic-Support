from __future__ import annotations

import asyncio

from packages.crew.support_flow import (
    run_support_flow,
)


async def main():

    result = await run_support_flow(
    session_id="SESSION_01",
    request_id="CREW_ACTION_TEST_001",
    question=(
        "Please open a support ticket "
        "to review the $35 activation fee on my bill."
        ),
    )

    print("=" * 80)
    print("TT&T CREWAI FLOW TEST")
    print("=" * 80)

    print()

    print(
        f"Route : {result['route']}"
    )

    print(
        f"Agent : {result['agent']}"
    )

    print()

    print("=" * 80)
    print("CUSTOMER ANSWER")
    print("=" * 80)

    print()

    print(
        result["answer"]
    )


if __name__ == "__main__":
    asyncio.run(main())