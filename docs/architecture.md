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
| `providers.yahoo` | Yahoo Public Client OAuth, PKCE/session, XML transport and league/settings/team/roster normalization. |
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
`name`, optional `sport`, optional `season`. Discovery does not introduce token,
GUID or raw Yahoo XML structures into the domain; FGM-004 separately normalizes
reported settings and roster observations. Malformed responses and HTTP
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

No scoring calculations, matchups, standings, transactions, external NHL data,
strategy, optimization, browser automation, persistent tokens, database, frontend,
hosted backend, production MCP deployment, or autonomous agents are implemented.

### FGM-004 verified team slice

The new `domain.team.Team` holds only provider, opaque league/team identity, and
name. `YahooFantasyClient.list_league_teams` normalizes a selected league's team
list; `list_my_league_teams` validates all user-scoped owned identities, filters
by the selected league, and cross-checks every matching team against the league
list. Multiple owned teams remain distinct. Missing, duplicate, inconsistent or
wrongly scoped identities reject the response with sanitized errors.

Both methods reuse the same bounded XML/GET implementation as discovery. The
private verifier shares their parsers and membership checks. No settings or
roster request is needed for these methods, and neither results nor tokens are
retained by the provider. Library logging is suppressed during Fantasy GETs and
restored on all exits. OAuth and MCP behavior are unchanged.

The human operator confirmed live league/team selection and the private CLI's
scoring, roster and position displays match Yahoo. Synthetic offline tests
validate the provider methods independently. Full scoring semantics, roster
completeness and lineup legality remain unverified. See the
[team contract history](fgm-004-team-contracts.md) and
[current application guide](fgm-004-private-cli.md) for the acceptance boundary.
No general provider framework, persistence or AI integration is introduced.

### Minimal roster envelope

`domain.roster` holds reported roster/entry/coverage facts without a completeness
or legality flag. The provider normalizes one selected owned team's bounded
response. The verifier shares normalization, records independent envelope/field
statuses and reuses the response for existing slot, position, coverage and human
checks. Missing dates remain missing, and supplied counts describe only returned
children. See the [roster contract](fgm-004-team-contracts.md#independent-roster-envelope-implemented-offline).
OAuth, the fixed read-path allowlist and Yahoo-backed MCP refusal are unchanged.

### Integrated private application

`python -B -m fantasy_gm.league --interactive` reuses the private terminal and
existing authorization flow, with discovered league and verified owned-team
selection. It reads ownership/membership once, settings once and one roster.
`providers.yahoo.settings` shares pure identity, stat/modifier, Decimal, scope
and slot parsing with the verifier. `domain.settings` holds immutable reported
configuration; independent unavailable sections are `None`. Partial scoring and
slot observations have explicit incomplete markers. Optional metadata failures
leave validated fields visible without certifying their complete interpretation.
No format mapping, scoring calculation or provider XML leaks into the domain.

Known competition flags are preserved outside stat weights. A supported roster
state with unresolved semantics sets `context_unverified`; it permits reported
facts but prevents semantic coverage/completeness certification. See the
[private application guide](fgm-004-private-cli.md). All new application behavior
has synthetic/offline validation and human-reported acceptance of displayed
information. No Yahoo-backed MCP integration is wired; acceptance does not
certify complete scoring semantics, coverage, completeness or lineup legality.

### FGM-005 independent schedule foundation

`providers.nhl.schedule` parses bounded catalogue/league windows into frozen
`domain.schedule` models. Pure `sports.nhl.schedule` functions calculate local-date
counts, opponents and B2B indicators; the standalone `fantasy_gm.schedule` command
renders the report. It has no Yahoo imports or authentication dependency.
Only an exact injected httpx.MockTransport is accepted; the CLI's labelled demo
generates fictitious games, while `--live` always rejects access. No real NHL
requests or live acceptance are claimed. The only dependency addition is tzdata.

Coverage records the timezone it qualifies. Counts, context completeness and
rankings are separate: unknown/missing observations cannot become proven zeros.
Domain exception states are retained without inventing NHL mappings or reschedule
history. Responses stay in memory. No cache, provider framework, polling, Yahoo
join or MCP exposure is introduced. See the [schedule guide](nhl-schedule.md).

### FGM-006 PuckAPI observations

`providers.puckapi` is a separate small REST adapter, reusing the existing
schedule models and pure analysis unchanged. The human CLI's explicit `--puckapi`
mode reads `PUCKAPI_API_KEY` at runtime and makes at most two fixed-origin POST
requests: current team catalogue and a bounded games query. The prior `--live`
NHL-operated mode remains disabled. No PuckAPI MCP connection is added.

REST envelopes, unique identities and current 32-club membership are validated.
Only aware full timestamps become UTC instants. Unknown states and unplaced
times remain visible; saturated result limits warn without automatic requests.
The candidate date padding does not qualify completeness: count/B2B completeness
and rankings stay unavailable until source coverage/date semantics are established.
Transport sizes, timeouts, cookies, logging, credentials and credits are bounded;
no responses or keys are persisted. Yahoo code and policies remain untouched.

The operator reports two successful weekly live CLI checks, including DST and
B2B reconciliation. This validates those observations only: HTTP success,
below-limit results and sampled agreement do not establish complete coverage.
An empty response remains an unqualified observation, with rankings suppressed.

### FGM-007 private roster schedules and session cache

The Yahoo roster provider retains optional normalized professional-team codes
and an explicit affiliation-uncertainty flag on `RosterEntry`. It consumes the
existing roster response; ownership, transport, OAuth and read paths are unchanged.
`sports.nhl.roster_schedule` joins these facts to a validated PuckAPI cohort and
uses the existing pure schedule analysis. Joined private rows never enter a cache.

`schedule_service.ScheduleService` owns at most four immutable public schedule
snapshots with an input-complete key and monotonic TTL. Expiration and refresh
evict before a fresh bounded PuckAPI client is created; errors are not cached,
and valid partial observations retain every coverage/truncation warning. It
receives no Yahoo identities, roster, credentials or raw response payloads.

`fantasy_gm.roster_schedule` reuses private terminal, authorization, discovered
league selection and owned-team roster retrieval. One Yahoo session is followed
by interactive roster/player/NHL-team views over shared schedule observations.
There is no automatic roster refresh, disk cache, background service, provider
framework or AI interface. Existing league and schedule CLIs remain unchanged.
See the [FGM-007 private guide](fgm-007-roster-schedule.md).
