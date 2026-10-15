"""Credential-free, in-memory MCP protocol verification with no LLM or Yahoo data."""

import asyncio
import sys
from pathlib import Path
from typing import Any

import anyio
import pytest
from anyio.abc import Process
from mcp import Client, StdioServerParameters

from fantasy_gm.mcp.server import create_server
from fantasy_gm.policy.yahoo import YahooAIAccessDenied, YahooAIPolicy


def test_server_health_capabilities_and_default_denial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("YAHOO_CLIENT_ID", "fake-client-id-for-tests")

    async def verify() -> None:
        async with Client(create_server(), cache=None) as client:
            listing = await client.list_tools()
            assert {tool.name for tool in listing.tools} == {
                "fantasy_gm_health",
                "fantasy_gm_capabilities",
                "yahoo_list_my_leagues",
            }
            health = await client.call_tool("fantasy_gm_health", {})
            assert not health.is_error and health.structured_content is not None
            assert health.structured_content["status"] == "ok"
            capabilities = await client.call_tool("fantasy_gm_capabilities", {})
            assert capabilities.structured_content is not None
            assert capabilities.structured_content["yahoo_configured"] is True
            assert capabilities.structured_content["yahoo_data_exposed"] is False
            assert capabilities.structured_content["yahoo_ai_tools_enabled"] is False
            denied = await client.call_tool("yahoo_list_my_leagues", {})
            assert denied.is_error
            rendered = denied.model_dump_json()
            assert "disabled pending provider-policy clarification" in rendered
            assert "fake-client-id-for-tests" not in rendered
            assert "access_token" not in rendered and "league_key" not in rendered

    asyncio.run(verify())


@pytest.mark.parametrize("value", ["false", "", "FALSE", "yes", "1", " true "])
def test_gate_denial_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("YAHOO_AI_TOOLS_ENABLED", value)
    assert YahooAIPolicy.from_environment().enabled is False

    async def verify() -> None:
        async with Client(create_server(), cache=None) as client:
            denied = await client.call_tool("yahoo_list_my_leagues", {})
            assert denied.is_error and "disabled pending" in denied.model_dump_json()

    asyncio.run(verify())


def test_explicit_true_still_cannot_expose_data_in_fgm003(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("YAHOO_AI_TOOLS_ENABLED", "true")
    assert YahooAIPolicy.from_environment().enabled is True

    async def verify() -> None:
        async with Client(create_server(), cache=None) as client:
            denied = await client.call_tool("yahoo_list_my_leagues", {})
            assert (
                denied.is_error and "not wired in FGM-003" in denied.model_dump_json()
            )

    asyncio.run(verify())


def test_policy_default_denies() -> None:
    with pytest.raises(YahooAIAccessDenied, match="disabled"):
        YahooAIPolicy().require_access()


@pytest.mark.parametrize("flag", [None, "false"])
def test_real_stdio_entrypoint_discovery_denial_and_clean_shutdown(
    monkeypatch: pytest.MonkeyPatch, flag: str | None
) -> None:
    processes: list[Process] = []
    original_open_process = anyio.open_process

    async def track_process(*args: Any, **kwargs: Any) -> Process:
        process = await original_open_process(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(anyio, "open_process", track_process)
    # Apply guards inside this child before importing/running the actual entrypoint.
    # Other subprocesses and general collection-time imports are not covered.
    bootstrap = "\n".join(
        [
            "import os, runpy, socket",
            "from pytest import MonkeyPatch",
            "from tests.conftest import (isolate_yahoo_environment, "
            "block_live_http, block_network_connections)",
            "guard = MonkeyPatch()",
            "isolate_yahoo_environment.__wrapped__(guard)",
            "block_live_http.__wrapped__(guard)",
            "block_network_connections.__wrapped__(guard)",
            *(["os.environ['YAHOO_AI_TOOLS_ENABLED'] = 'false'"] if flag else []),
            "try:",
            "    with socket.socket() as probe:",
            "        probe.connect(('127.0.0.1', 0))",
            "except AssertionError:",
            "    pass",
            "else:",
            "    raise RuntimeError('Child network guard is inactive')",
            "runpy.run_module('fantasy_gm.mcp', run_name='__main__')",
        ]
    )
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-B", "-c", bootstrap],
        cwd=Path(__file__).resolve().parents[1],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )

    async def verify() -> None:
        with anyio.fail_after(20):
            async with Client(
                parameters, cache=None, read_timeout_seconds=5.0
            ) as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "fantasy_gm_health",
                    "fantasy_gm_capabilities",
                    "yahoo_list_my_leagues",
                }
                health = await client.call_tool("fantasy_gm_health", {})
                assert not health.is_error
                assert health.structured_content is not None
                assert health.structured_content["status"] == "ok"
                capabilities = await client.call_tool("fantasy_gm_capabilities", {})
                assert capabilities.structured_content is not None
                assert capabilities.structured_content["yahoo_configured"] is False
                assert capabilities.structured_content["yahoo_data_exposed"] is False
                assert (
                    capabilities.structured_content["yahoo_ai_tools_enabled"] is False
                )
                denied = await client.call_tool("yahoo_list_my_leagues", {})
                assert denied.is_error
                assert (
                    "disabled pending provider-policy clarification"
                    in denied.model_dump_json()
                )
        assert len(processes) == 1
        assert processes[0].returncode == 0, "Server did not exit cleanly on stdin EOF"

    asyncio.run(verify())
