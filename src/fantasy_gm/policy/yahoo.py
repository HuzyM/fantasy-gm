"""Central, fail-closed gate for Yahoo Fantasy information in AI interfaces."""

import os
from dataclasses import dataclass

YAHOO_AI_DENIAL = (
    "Yahoo-backed AI access is disabled pending provider-policy clarification."
)


class YahooAIAccessDenied(Exception):
    """No Yahoo information is included in this error."""


@dataclass(frozen=True)
class YahooAIPolicy:
    enabled: bool = False

    @classmethod
    def from_environment(cls) -> "YahooAIPolicy":
        # Only an explicit literal true opts in; credentials never enable access.
        return cls(enabled=os.environ.get("YAHOO_AI_TOOLS_ENABLED", "false") == "true")

    def require_access(self) -> None:
        if not self.enabled:
            raise YahooAIAccessDenied(YAHOO_AI_DENIAL)
