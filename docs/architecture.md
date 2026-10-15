# Intended architecture

Fantasy GM is a provider-independent core with thin interfaces and replaceable
integrations. The diagram describes future responsibilities, not implemented
services or frameworks.

```text
AI Client
    |
    | MCP
    v
Fantasy GM MCP
    |
    v
Fantasy GM Core
    |
    +-- Provider Layer
    |      +-- Yahoo
    |      +-- future ESPN
    |      +-- future Sleeper
    |
    +-- Sport Intelligence
    |      +-- NHL
    |
    +-- Strategy Engine
    |
    +-- Weekly Optimizer
    |
    +-- Policy / Transaction Safety Layer
```

## Package responsibilities

| Namespace | Intended responsibility |
| --- | --- |
| `config` | Explicit Pydantic configuration, including Yahoo OAuth environment settings. |
| `domain` | Fantasy GM's own Pydantic domain types. |
| `providers` | Provider access and normalization into domain types. |
| `providers.yahoo` | Yahoo Public Client OAuth, PKCE/session, XML discovery transport and normalization. |
| `sports` / `sports.nhl` | Sport-specific schedule, player, and matchup context. |
| `strategy` | Analysis consuming domain types. |
| `optimizer` | Weekly roster optimization consuming domain types. |
| `policy` | Access constraints and transaction safety rules. |
| `mcp` | A thin interface exposing core capabilities to AI clients. |

## Boundaries and sources of truth

1. Yahoo-specific models must never become core domain models. Each provider
   will translate its data into Fantasy GM's domain types at the provider boundary.
2. Strategy and optimization must depend on the domain layer, without importing
   Yahoo-specific transport or models. Providers must remain replaceable.
3. The domain layer will be the shared source of truth for normalized types.
   Keep provider payloads confined to their integrations.
4. MCP is an interface into Fantasy GM, not the core architecture. The official
   Python MCP SDK supplies the local stdio server; its tools do not import Yahoo
   transport or token models. Yahoo data exposure requires centralized policy
   handling and remains unwired in FGM-003.
5. Transaction/write functionality depends on provider-supported access. Future
   implementation must respect that access and the policy layer.
6. Never put credentials, tokens, OAuth secrets, cookies, or personal Yahoo data
   into source control.

## Incremental implementation

Implement only what each approved task needs. FGM-003 corrects the FGM-002 OAuth
foundation for the confirmed Public Client, adds manual current-season hockey
league discovery, one normalized league model, and local MCP health/capability
tools. Sports, strategy, and optimizer remain placeholders. There are no generic
provider protocols, plugin registries, or dependency injection frameworks.

### Yahoo OAuth boundary

OAuth transport, endpoints, token models, and narrowly scoped errors live in
`providers.yahoo.oauth`, with PKCE and one-attempt sessions in adjacent modules.
The domain layer does not import them. Only the Public Client ID is required by
`config.yahoo.YahooOAuthConfig`; no environment loading
occurs during imports, and `.env` is not loaded automatically.

The OAuth client receives a caller-owned `httpx.Client`, allowing tests to inject
`httpx.MockTransport` without another mocking dependency. Token requests use form
encoding with `client_id`, the canonical redirect, and (for code exchange) the
PKCE verifier per Yahoo's current
[Public Client documentation](https://developer.yahoo.com/sign-in-with-yahoo/).
Client secrets and inherited HTTP client authentication are omitted.
Requests have a bounded timeout, do not follow redirects, and are not retried
automatically. Errors omit provider bodies and underlying transport messages.

Tokens use masked `SecretStr` fields and exist only in memory. Expiration is
represented as the returned `expires_in` lifetime in seconds. Additional Yahoo
response fields are ignored rather than promoted into domain models. Refresh
responses preserve any newly issued refresh token; if Yahoo omits one, the previous
refresh token is retained. No automatic refresh loop or persistent lifecycle is
implemented.

`YahooAuthorizationSession` generates random state and a random 32-byte PKCE value
encoded as a 43-character verifier. Only S256 is supported, without base64 padding.
State comparison uses constant-time comparison before the token request. A session
allows one exchange attempt, including invalid-state or failed-network attempts;
retrying requires a fresh session. State/verifier are never persisted or logged.
The redirect is fixed to the confirmed HTTPS URL. No scopes are sent: Fantasy
Sports - Read is configured on the Yahoo application. No callback backend exists.

The static GitHub Pages callback at
`https://huzym.github.io/fantasy-gm/oauth/callback/` is a manual handoff page in
`docs/oauth/callback/index.html`. It displays a code/state or error using text-only
rendering and removes OAuth query parameters from the current history entry.
It does not transmit, persist, exchange, or validate the response; the user copies
the code and returns to the local application. State validation remains the
local caller's responsibility. The initial redirect is still received by the
hosting provider. This static page adds no dependency to the core or provider.

### Human CLI and provider/domain boundary

`python -m fantasy_gm.auth` is a deterministic, human-operated flow independent of
MCP. It prints the authorization URL, accepts code/state through hidden prompts,
validates state, exchanges the code, and makes one authenticated read-only request.
It disables library logging during execution and refuses redirected input/output.
Only league key, name, sport, and season reach the terminal, with Yahoo attribution.

`providers.yahoo.fantasy` uses the documented user-scoped URI
`users;use_login=1/games;game_keys=nhl/leagues` under the Fantasy API v2 base.
Yahoo's [User APIs and Games collection documentation](https://sports.yahoo.com/developer/docs/)
describe this hierarchy and the `nhl` game-code alias for the current season.
The request uses Bearer authorization and asks for XML. It discovers only the
logged-in user's current hockey game; historical-season enumeration is excluded.
API responses can include additional default league metadata. It is parsed in
memory and discarded, not promoted into domain types.

Yahoo's XML hierarchy and `YahooLeagueMetadata` remain inside the provider.
The provider returns `domain.league.League`: `provider`, `provider_league_id`,
`name`, optional `sport`, optional `season`. No token, GUID, scoring, roster, or
other Yahoo response structures enter the domain. Malformed responses and HTTP
failures produce sanitized errors without provider bodies. DTD/entity declarations
are rejected. HTTP requests have a bounded timeout, no redirect following, no
automatic retries, and no cache.

Discovery streams at most 1 MiB of unencoded XML before parsing, regardless of
`Content-Length`. It requests `identity` encoding and rejects compressed responses
before reading to avoid unbounded decompression. The parser checks each required
users/games/leagues wrapper and its resource children in one of Yahoo's documented
HTTP/HTTPS XML namespaces. If a response supplies `count`, it must match the
returned children; the attribute is not mandatory. Legitimate empty collections
remain valid, while any malformed nested collection rejects the whole response.
Unconsumed optional metadata is ignored.

### Data lifetime and MCP policy

Yahoo response → parse in memory → normalize in memory → use in the current
process → discard. No database, file dumps, persistence, cache, index, captured
live fixtures, or Yahoo-data telemetry exists. This applies even to ignored local
directories. Tokens likewise remain in memory for the process lifetime.

`mcp.server.create_server()` uses the official Python MCP SDK. Health and
capabilities tools return safe package/configuration status, never Yahoo data or
credential values. The stdio entry point is `python -m fantasy_gm.mcp`; no HTTP
server or production deployment is added.

`policy.yahoo.YahooAIPolicy` defaults to denied. Only exact `true` explicitly
opts into the gate; missing, false, or malformed values fail closed. Credentials
never enable it. The `yahoo_list_my_leagues` stub returns a clean denial by
default, and stays unwired even with explicit opt-in in FGM-003. It accepts no
tokens and never calls Yahoo. Future exposure requires written provider-policy
clarification and a separately approved implementation.

The confirmed technical constraints are personal use, read-only access to the
developer's own leagues/teams, no stored/cached/indexed Yahoo Fantasy information,
and no commercial or multi-user Yahoo functionality. Future displays need Yahoo
attribution. Yahoo-backed AI access remains disabled pending clarification of the
agreement's AI-grounding language. These constraints are not legal interpretation.

The [manual verification guide](yahoo-verification.md) describes the human-only
milestone and current-season limitation. Synthetic tests verify protocol
construction, not live permission, token issuance/rotation, or actual league access.

The current foundation uses Python 3.12+, a `src/` package layout, uv dependency
management and its build backend, Pydantic, httpx, and the official MCP SDK.
Pytest, Ruff, and strict
mypy provide development checks. `pyproject.toml` holds project/tool settings;
`uv.lock` holds resolved dependency versions.

No roster, scoring settings, matchups, players, standings, transactions, NHL data,
strategy, optimization, browser automation, persistent tokens, database, frontend,
hosted backend, production MCP deployment, or autonomous agents are implemented.
