from __future__ import annotations

import json

from packages.mcp_server.outage_tools import (
    get_outages,
)


def run_test(
    postal_code: str,
    include_resolved: bool = False,
):

    print("=" * 80)
    print("TT&T OUTAGE TOOL TEST")
    print("=" * 80)

    print(
        f"\nPostal code: {postal_code}"
    )

    print(
        f"Include resolved: "
        f"{include_resolved}\n"
    )

    result = get_outages(
        postal_code=postal_code,
        include_resolved=include_resolved,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


def main():

    run_test(
        postal_code="00003"
    )


if __name__ == "__main__":
    main()