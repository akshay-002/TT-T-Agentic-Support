from __future__ import annotations

import json

from packages.mcp_server.invoice_tools import (
    get_invoice_comparison,
)


def main():

    account_id = "ACC_1006"


    print("=" * 80)
    print("TT&T INVOICE COMPARISON TOOL TEST")
    print("=" * 80)

    print(
        f"\nAccount: {account_id}\n"
    )


    result = get_invoice_comparison(
        account_id
    )


    print(
        json.dumps(
            result,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()