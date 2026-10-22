"""Fail closed on absent, duplicate or unfinished required check evidence."""

import importlib.util
import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

_spec = importlib.util.spec_from_file_location(
    "pr_status", Path(__file__).parents[1] / "scripts" / "pr_status.py"
)
assert _spec and _spec.loader
pr_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr_status)


def payload() -> dict[str, Any]:
    return {
        "number": 32,
        "state": "OPEN",
        "headRefOid": "a" * 40,
        "statusCheckRollup": [
            {"name": name, "status": "COMPLETED", "conclusion": "SUCCESS"}
            for name in pr_status.CHECK_NAMES
        ],
        "body": "DO NOT PRINT" * 10000,
        "comments": ["DO NOT PRINT"],
        "diff": "DO NOT PRINT",
    }


def test_summary_is_bounded_and_excludes_content() -> None:
    result = pr_status.summarize(payload())
    assert result["ci_passed"] is True
    assert result["head"] == "a" * 40
    assert len(json.dumps(result)) < 600
    assert "DO NOT PRINT" not in json.dumps(result)


@pytest.mark.parametrize(
    "failure", ["missing", "duplicate", "pending", "failed", "skipped"]
)
def test_required_checks_fail_closed(failure: str) -> None:
    data = payload()
    checks = data["statusCheckRollup"]
    if failure == "missing":
        checks.pop()
    elif failure == "duplicate":
        checks.append(checks[0].copy())
    elif failure == "pending":
        checks[0]["status"] = "IN_PROGRESS"
    else:
        checks[0]["conclusion"] = failure.upper()
    assert pr_status.summarize(data)["ci_passed"] is False


def test_cli_rejects_head_changed_during_query(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["pr_status.py", "32"])
    run = Mock(
        side_effect=[
            Mock(stdout=json.dumps(payload())),
            Mock(stdout=json.dumps({"headRefOid": "b" * 40})),
        ]
    )
    monkeypatch.setattr(pr_status.subprocess, "run", run)
    assert pr_status.main() == 1
    out = capsys.readouterr()
    assert not out.out
    assert "unavailable_or_changed" in out.err
    assert "DO NOT PRINT" not in out.err
    assert run.call_args_list[0].args[0][-1] == pr_status.FIELDS
