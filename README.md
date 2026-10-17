# Fantasy GM

Fantasy GM is a fantasy sports analytics and management platform designed to connect real fantasy league data with schedule, player, matchup, and roster intelligence. The initial integration targets Yahoo Fantasy Hockey.

**Status: FGM-004 supported read-only workflow accepted.** Yahoo Public Client
OAuth with PKCE, current-season NHL league discovery, owned-team selection,
reported league settings/scoring and player/position views are implemented.
The human operator confirmed the private CLI displays the expected information
and matches Yahoo. Automated validation uses synthetic data only; this acceptance
does not establish every scoring rule, roster completeness or lineup legality.
Yahoo Fantasy information is not exposed through MCP.

## Planned capabilities

- Yahoo Fantasy Hockey integration
- Matchup analysis
- Available-player analysis
- Weekly roster optimization
- Add/drop and trade analysis
- MCP interface for AI assistants

Future integrations may support **ESPN** and **Sleeper**, with sport intelligence
for **NBA, NFL, and MLB** alongside NHL.

Transaction/write functionality depends on provider-supported access. Analysis
does not imply that a provider allows transaction execution.

## Architecture

Provider integrations will normalize external data into Fantasy GM's own domain
types. Strategy and optimization will consume those types, keeping Yahoo details
out of the core. Sport intelligence will provide sport-specific context. Policy
will hold transaction safety rules when transaction functionality is introduced.
MCP will expose core capabilities to AI clients as an interface.

Yahoo configuration and models use Pydantic; the Yahoo provider uses httpx for
OAuth and fixed read-only league/settings/team/roster endpoints. Domain models
hold normalized identities and reported configuration/roster observations.
The official Python MCP SDK supplies the local
stdio interface, with a centralized policy gate for Yahoo data. Sport intelligence,
strategy, and optimization remain placeholders.
See [the architecture document](docs/architecture.md) for the intended boundaries.

## Development setup

Install Python **3.12+** and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The default development interpreter is Python 3.12.

From the repository root:

```sh
uv sync --locked
uv run python -c "import fantasy_gm; print('Fantasy GM imports successfully')"
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

`uv sync` installs the package and development dependencies into `.venv`.
Commit `uv.lock` to keep dependency versions reproducible. Build distributions
with `uv build` when needed.

## Yahoo Public Client authorization

Set only `YAHOO_CLIENT_ID` in the local environment. The confirmed Yahoo application
is a **Public Client**, with **Fantasy Sports - Read** permission. It does not
require or transmit a client secret. The exact registered redirect is an application
constant; legacy secret/redirect environment values are ignored. Configuration
does not load `.env` automatically. `.env.example` has a blank client ID and the
safe `YAHOO_AI_TOOLS_ENABLED=false` default. Never commit real application values,
authorization codes, tokens, or PKCE verifiers.

`YahooAuthorizationSession` keeps random state and an S256 PKCE verifier/challenge
in memory. The local flow consumes the session once and validates returned state
before exchanging the code. Token requests follow Yahoo's current
[Public Client OAuth documentation](https://developer.yahoo.com/sign-in-with-yahoo/),
omit client secrets and inherited client authentication, and use the registered
redirect. No OIDC, profile, email, or write scopes are requested. Refresh preserves
a newly returned refresh token, or the previous token when Yahoo omits one.

Token responses are streamed with a 64 KiB maximum regardless of Content-Length.
The client requests identity encoding and rejects compressed responses before
reading; responses close on success or failure. Access tokens must use Bearer
token syntax before discovery can use them in an Authorization header.

Token values are held in memory as Pydantic `SecretStr` fields, which mask normal
representation and JSON serialization. `expires_in` records the token lifetime
in seconds. There is no token storage or automatic refresh. Never log tokens,
authorization codes, PKCE verifiers, HTTP auth headers, or request
and response bodies; debug tooling can bypass model masking.

The human-operated `uv run --locked python -m fantasy_gm.auth` flow uses hidden
code/state prompts, then prints minimal metadata for the developer's current
Yahoo hockey leagues. It requires an interactive terminal and refuses redirected
input/output. No browser is opened automatically and no data is saved. See the
[manual verification guide](docs/yahoo-verification.md) before authorizing; automated
tests do not authorize Yahoo or make live HTTP requests.

League discovery streams unencoded XML with a 1 MiB maximum, counting received
bytes rather than trusting `Content-Length`. Compressed responses are rejected
before reading. Required collection structure, namespaces, and any supplied
collection counts are checked; malformed collections fail instead of appearing
as empty results. The developer reported successful live league parsing; other
accounts, empty live collections, and future response changes remain unverified.

A separate [private NHL contract verifier](docs/nhl-contract-verification.md)
remains available for explicitly approved human contract investigation. It is
stricter than the application view and does not certify partial observations.
It is not required to repeat the accepted private CLI workflow. Its shareable
output uses fixed statuses and codes, never Yahoo response data.

## Private league and roster application

The human-only FGM-004 application is available with
`uv run --locked --offline python -B -m fantasy_gm.league --interactive`.
It shows supported league flags, untranslated scoring format, exact Decimal
modifier literals, display-only flags, position applicability and slot capacities,
plus player identities and eligible/assigned positions. Missing or unsupported
fields stay unknown; incomplete sections show explicit partial warnings without
hiding independent information. No scoring calculations or lineup decisions occur.
See the [private application guide](docs/fgm-004-private-cli.md) for the Windows
command, privacy requirements and acceptance boundaries.

The human operator confirmed league and owned-team selection, scoring settings,
player roster and roster positions work and match Yahoo. This is human-reported
live acceptance for displayed information; the automated suite is offline and
synthetic. Other leagues/rules, effective coverage, reserve inclusion/completeness,
lineup legality and transactions remain unverified or unimplemented.

## Local MCP and Yahoo data policy

Start the stdio server with `uv run --locked python -m fantasy_gm.mcp` through a
local MCP client. `fantasy_gm_health` and `fantasy_gm_capabilities` return package
information and supported features, never league data or credential values.
`yahoo_list_my_leagues` is a refusal stub. With the AI flag absent or `false`, it
explains that Yahoo-backed AI access is disabled pending provider-policy
clarification. Even an explicit `true` does not wire it to Yahoo in FGM-003.

Under the confirmed approval, the integration is personal, read-only, and limited
to the developer's own leagues/teams. Yahoo Fantasy information is parsed and
normalized in memory for the current process, then discarded: no persistence,
cache, index, recorded live fixtures, or telemetry containing Yahoo data.
Commercial and multi-user Yahoo functionality is excluded. Future interfaces
displaying Yahoo information must satisfy Yahoo attribution requirements; the
manual CLI identifies Yahoo as the data source. Yahoo-backed AI/MCP data exposure
remains disabled pending written clarification of the agreement's AI-grounding
language. These are technical project constraints, not legal interpretation.

### Yahoo Developer callback page

Yahoo Developer redirect URI (including the trailing slash):

```text
https://huzym.github.io/fantasy-gm/oauth/callback/
```

The static page in `docs/oauth/callback/index.html` displays the authorization
code, returned state, or Yahoo error. It removes `code`, `state`, `error`, and
`error_description` from the current browser URL before displaying the response.
Copy the code and returned state, and return to the running local Fantasy GM
application. The local session validates state; the page only displays it.
Refreshing the cleaned URL discards the response.

The page has no API calls, external scripts, analytics, or browser storage.
Authorization data is kept in memory; copying to the clipboard happens only on
request. Treat the code and clipboard contents as sensitive and close the tab
after use. GitHub Pages receives the initial redirect URL as the hosting provider;
client-side URL cleanup cannot erase hosting infrastructure logs.

After these files are merged into `main`, enable GitHub Pages under repository
**Settings → Pages → Build and deployment**. Choose **Deploy from a branch**,
branch **main**, folder **/docs**, and **Save**. Wait for deployment and confirm
the exact HTTPS callback URL opens before using it for registration. Leave the
custom domain unset to retain the URL above and enable **Enforce HTTPS** when
available. See [GitHub's publishing-source instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

The static page performs no token exchange or league discovery. Those requests
are confined to the manually started local process.

## Security

Never commit `.env`, credentials, OAuth secrets, tokens, cookies, or personal
Yahoo data. Yahoo Fantasy information must not be saved even in ignored `data/`
or `local/` directories. Review staged files before committing. Ignore rules are
a safeguard, not a substitute for that review. Tests use synthetic values and
block HTTP transports, socket connections, DNS, and async network connections
during test execution. The private local wakeup pair needed for Windows asyncio
uses one exact socket/listener connection without relaxing the global guard.
The real MCP stdio smoke-test child installs its own guards before starting the
server. General collection-time imports and arbitrary subprocesses are outside
these fixture guards; this is not an operating-system network sandbox.

## NHL schedules (FGM-005/006)

Try independent schedule counts, opponents, daily games and back-to-back views
without Yahoo authentication:

```powershell
uv run --locked --offline python -m fantasy_gm.schedule --demo --season 20262027 --from 2026-11-01 --to 2026-11-07 --view counts
```

This is an explicitly synthetic 32-club demonstration, not real NHL data.
America/Toronto is the default display zone; UTC instants and DST conversion are
supported. `--puckapi` retrieves real observations using the runtime
`PUCKAPI_API_KEY`; the key belongs only in a private shell session. PuckAPI uses
documented authenticated REST, normally two requests / six credits per run.
Coverage remains explicitly partial; reaching the result cap adds a warning.
Time-only timestamps are never assigned a guessed timezone. The operator reports
successful live acceptance for two weekly windows, including DST/B2B checks;
this does not establish a complete-coverage contract. Exit 1 remains expected
for partial observations, including valid empty results. `--live` continues to
reject the NHL-operated source. No calendar imports, Yahoo data joins or AI tools are added.
See the
[schedule guide](docs/nhl-schedule.md) for views, meanings and limitations.

## Private roster schedules (FGM-007)

The new human-only `python -B -m fantasy_gm.roster_schedule --interactive`
workflow authorizes Yahoo once and uses professional-team metadata from the
existing roster response to show observed NHL schedules for supported players.
Player and NHL-team views share a bounded four-entry in-memory PuckAPI cache,
with a configurable one-hour TTL and explicit manual refresh. No roster or
credential is cached, persisted or sent to PuckAPI/AI; only public schedule
observations are cached. Missing affiliations and coverage remain unknown.
The operator reports successful private live acceptance of authentication,
affiliation matching, observed counts, player selection, cache/refresh, input
retries, BACK navigation and exit. Complete totals and B2B coverage remain unknown.
See the [private guide](docs/fgm-007-roster-schedule.md) for secure shell commands,
cache statuses, request budgets, acceptance checks and remaining limitations.

## License

All rights reserved pending the project owner's choice of license. See `LICENSE`.
