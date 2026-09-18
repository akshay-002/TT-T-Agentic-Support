from __future__ import annotations

import json

from packages.mcp_server.ticket_tools import (
    create_support_ticket,
)


def main():

    result = create_support_ticket(
        account_id="ACC_1001",
        line_id="LINE_2001",
        category="billing",
        summary=(
            "Customer disputes the $35 activation fee "
            "and requests a billing review."
        ),
        idempotency_key=(
            "TEST_TICKET_ACC_1001_001"
        ),
    )

    print("=" * 80)
    print("TT&T CREATE SUPPORT TICKET TEST")
    print("=" * 80)

    print()

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()