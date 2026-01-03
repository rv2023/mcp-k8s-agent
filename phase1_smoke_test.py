# phase1_smoke_test.py
from __future__ import annotations

import sys
import tools_read


def main() -> int:
    ns = sys.argv[1] if len(sys.argv) > 1 else "default"

    print(f"\n[1] list pods in namespace={ns}")
    ctype, text = tools_read.list_resources(
        namespace=ns,
        group="",
        version="v1",
        plural="pods",
        kind="Pod",
    )
    print(text[:2000])

    print(f"\n[2] list events in namespace={ns}")
    ctype, text = tools_read.list_events(namespace=ns)
    print(text[:2000])

    print("\n[3] forbidden plural should fail: secrets")
    try:
        tools_read.list_resources(
            namespace=ns,
            group="",
            version="v1",
            plural="secrets",
            kind="Secret",
        )
        print("UNEXPECTED: secrets allowed")
        return 2
    except Exception as e:
        print(f"expected failure: {type(e).__name__}: {e}")

    print("\nDONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())