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
| `providers.yahoo` | Yahoo OAuth transport and token models; future Fantasy API integration. |
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
   Python MCP SDK can be added as an optional dependency when that interface is
   implemented; no SDK, server, or tools are included now.
5. Transaction/write functionality depends on provider-supported access. Future
   implementation must respect that access and the policy layer.
6. Never put credentials, tokens, OAuth secrets, cookies, or personal Yahoo data
   into source control.

## Incremental implementation

Implement only what each approved task needs. FGM-002 adds explicit Yahoo OAuth
configuration and a small Yahoo-specific OAuth client. All other namespaces
remain package placeholders. There are no speculative domain models, provider
protocols, plugin registries, or dependency injection frameworks.

### Yahoo OAuth boundary

OAuth transport, endpoints, token models, and narrowly scoped errors live in
`providers.yahoo.oauth`. The domain layer does not import them. OAuth credentials
are read explicitly by `config.yahoo.YahooOAuthConfig`; no environment loading
occurs during imports, and `.env` is not loaded automatically.

The OAuth client receives a caller-owned `httpx.Client`, allowing tests to inject
`httpx.MockTransport` without another dependency. Token requests use HTTP Basic
client authentication and form encoding per Yahoo's
[OAuth authorization code documentation](https://developer.yahoo.com/oauth2/guide/flows_authcode/).
Requests have a bounded timeout, do not follow redirects, and are not retried
automatically. Errors omit provider bodies and underlying transport messages.

Tokens use masked `SecretStr` fields and exist only in memory. Expiration is
represented as the returned `expires_in` lifetime in seconds. Additional Yahoo
response fields are ignored rather than promoted into domain models. Refresh
responses preserve any newly issued refresh token; if Yahoo omits one, the
returned optional field is `None`. Retaining a previous refresh token when
appropriate belongs to a future token lifecycle caller, not this transport.

The authorization URL requires caller-supplied state; generating, retaining, and
validating unpredictable state belongs to a future authorization flow. Redirect
URIs preserve their exact configured spelling and support HTTP(S) URLs or Yahoo's
documented `oob` value. No callback server or complete local authentication flow
is included.

The static GitHub Pages callback at
`https://huzym.github.io/fantasy-gm/oauth/callback/` is a manual handoff page in
`docs/oauth/callback/index.html`. It displays a code/state or error using text-only
rendering and removes OAuth query parameters from the current history entry.
It does not transmit, persist, exchange, or validate the response; the user copies
the code and returns to the local application. State validation remains the
local caller's responsibility. The initial redirect is still received by the
hosting provider. This static page adds no dependency to the core or provider.

Before league discovery, verify app approval and Fantasy Sports permissions,
registered redirect/callback support (including whether `oob` is accepted for this
app), current PKCE requirements, and actual token response/refresh behavior with
approved credentials. Mocked tests verify protocol construction, not live access.

The current foundation uses Python 3.12+, a `src/` package layout, uv dependency
management and its build backend, Pydantic, and httpx. Pytest, Ruff, and strict
mypy provide development checks. `pyproject.toml` holds project/tool settings;
`uv.lock` holds resolved dependency versions.

No Yahoo Fantasy API requests, league discovery, NHL integration, strategy,
optimization, transaction execution, browser automation, token persistence,
database, frontend, Docker, MCP tools, or autonomous agents are implemented.
