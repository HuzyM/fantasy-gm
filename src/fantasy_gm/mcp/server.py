"""Local stdio MCP interface. No Yahoo credentials or data are accepted as tools."""

import os
from importlib.metadata import version

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from fantasy_gm.policy.yahoo import YAHOO_AI_DENIAL, YahooAIAccessDenied, YahooAIPolicy


def create_server() -> MCPServer[None]:
    policy = YahooAIPolicy.from_environment()
    server: MCPServer[None] = MCPServer("Fantasy GM", version=version("fantasy-gm"))
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, open_world_hint=False
    )

    @server.tool(annotations=annotations)
    def fantasy_gm_health() -> dict[str, str]:
        """Report local package/server health without Yahoo data."""
        return {
            "status": "ok",
            "package": "fantasy-gm",
            "version": version("fantasy-gm"),
        }

    @server.tool(annotations=annotations)
    def fantasy_gm_capabilities() -> dict[str, object]:
        """Report capabilities, never league information or secrets."""
        return {
            "providers": ["yahoo"],
            "sports": ["nhl"],
            "features": ["public_client_pkce", "manual_auth", "local_league_discovery"],
            "yahoo_configured": bool(os.environ.get("YAHOO_CLIENT_ID", "").strip()),
            "yahoo_read_only": True,
            "yahoo_ai_tools_enabled": policy.enabled,
            "yahoo_data_exposed": False,
            "token_persistence": False,
        }

    @server.tool(annotations=annotations)
    def yahoo_list_my_leagues() -> dict[str, object]:
        """Reserved Yahoo data tool: denied by default and unwired in FGM-003."""
        try:
            policy.require_access()
        except YahooAIAccessDenied:
            raise ToolError(YAHOO_AI_DENIAL) from None
        # Opt-in still cannot expose data before provider policy is resolved.
        raise ToolError(
            "Yahoo-backed MCP discovery is not wired in FGM-003; "
            "provider-policy clarification is required before any data exposure."
        )

    return server
