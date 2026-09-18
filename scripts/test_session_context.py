from __future__ import annotations

from dataclasses import asdict
import json

from packages.security.session_context import (
    resolve_session,
)


def main():

    context = resolve_session(
        "SESSION_06"
    )

    print("=" * 80)
    print("TT&T SESSION CONTEXT TEST")
    print("=" * 80)

    print()

    print(
        json.dumps(
            asdict(context),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()