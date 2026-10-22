"""Print a bounded PR/check summary without fetching diffs, bodies or comments."""

import argparse
import json
import subprocess
import sys
from typing import Any

CHECK_NAMES = ("Python Linux", "Frontend and local API", "Python Windows and browser")
FIELDS = "number,state,headRefOid,statusCheckRollup"


def summarize(payload: dict[str, Any]) -> dict[str, Any]:
    """Project only workflow metadata; unknown payload fields never reach output."""
    checks = payload.get("statusCheckRollup", [])
    if not isinstance(checks, list):
        raise ValueError("invalid check list")
    required = {}
    for name in CHECK_NAMES:
        matches = [c for c in checks if isinstance(c, dict) and c.get("name") == name]
        # Ambiguous contexts need inspection; never pick a convenient passing row.
        if len(matches) != 1:
            required[name] = "missing" if not matches else "ambiguous"
        else:
            check = matches[0]
            required[name] = (
                "passed"
                if check.get("status") == "COMPLETED"
                and check.get("conclusion") == "SUCCESS"
                else "not_passed"
            )
    head = payload.get("headRefOid")
    if not isinstance(head, str) or len(head) != 40:
        raise ValueError("missing full head SHA")
    if any(c not in "0123456789abcdef" for c in head):
        raise ValueError("invalid head SHA")
    number = payload.get("number")
    if type(number) is not int or number < 1:
        raise ValueError("invalid PR number")
    state = payload.get("state")
    if state not in ("OPEN", "CLOSED", "MERGED"):
        raise ValueError("invalid PR state")
    return {
        "number": number,
        "state": state,
        "head": head,
        "required_checks": required,
        "ci_passed": all(value == "passed" for value in required.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", type=int)
    args = parser.parse_args()
    if args.pr < 1:
        parser.error("pr must be positive")
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(args.pr), "--json", FIELDS],
            capture_output=True,
            check=True,
            timeout=30,
            encoding="utf-8",
        )
        snapshot = summarize(json.loads(result.stdout))
        # Reject a snapshot if a concurrent push changed the PR while checks loaded.
        current = subprocess.run(
            ["gh", "pr", "view", str(args.pr), "--json", "headRefOid"],
            capture_output=True,
            check=True,
            timeout=30,
            encoding="utf-8",
        )
        if json.loads(current.stdout).get("headRefOid") != snapshot["head"]:
            raise ValueError("head changed")
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, AttributeError):
        print('{"status":"unavailable_or_changed"}', file=sys.stderr)
        return 1
    print(json.dumps(snapshot, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
