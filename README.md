# Fantasy GM

Fantasy GM is a fantasy sports analytics and management platform designed to connect real fantasy league data with schedule, player, matchup, and roster intelligence. The initial integration targets Yahoo Fantasy Hockey.

**Status: early development.** The project foundation and Yahoo OAuth component
are implemented and tested with mocked HTTP. Live Yahoo access has not been
verified; the fantasy-data capabilities below are planned and are not implemented.

## Planned capabilities

- Yahoo Fantasy Hockey integration
- League and scoring settings
- Roster retrieval
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

Yahoo OAuth configuration uses Pydantic; the Yahoo provider uses httpx for token
requests. The domain, sport intelligence, strategy, optimization, policy, and MCP
namespaces remain lightweight placeholders.
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

## Yahoo OAuth foundation

Credentials will be supplied through the `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`,
and `YAHOO_REDIRECT_URI` environment variables. Never commit their real values.
`YahooOAuthConfig.from_environment()` validates these variables explicitly;
it does not read `.env` files or supply fallback credentials. `.env.example`
continues to contain blank placeholders only. Tests require no Yahoo credentials
and block live httpx transports.

`YahooOAuthClient` in `providers.yahoo.oauth` accepts configuration and a
caller-owned `httpx.Client`. It builds authorization URLs, exchanges authorization
codes, and refreshes tokens using Yahoo's documented
[authorization code flow](https://developer.yahoo.com/oauth2/guide/flows_authcode/).
Use a mock transport for testing. The caller must supply unpredictable OAuth
`state` and validate the returned state before exchanging a code. The static
callback page described below supports manual code transfer only; the local
application does not yet implement a complete authorization flow.

Token values are held in memory as Pydantic `SecretStr` fields, which mask normal
representation and JSON serialization. `expires_in` records the token lifetime
in seconds. There is no token storage, automatic refresh, browser flow, or fantasy
API access. Never log tokens, authorization codes, HTTP auth headers, or request
and response bodies; debug tooling can bypass model masking.

### Yahoo Developer callback page

Yahoo Developer redirect URI (including the trailing slash):

```text
https://huzym.github.io/fantasy-gm/oauth/callback/
```

The static page in `docs/oauth/callback/index.html` displays the authorization
code, returned state, or Yahoo error. It removes `code`, `state`, `error`, and
`error_description` from the current browser URL before displaying the response.
Copy the code, verify the returned state against your original local request,
and return to the local Fantasy GM application. State is displayed, not validated
by this page. Refreshing the cleaned URL discards the response.

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

This page does not change Yahoo OAuth configuration, implement token exchange,
or introduce league discovery.

## Security

Never commit `.env`, credentials, OAuth secrets, tokens, cookies, or personal
Yahoo data. Keep local data under ignored `data/` or `local/` directories and
review staged files before committing. Ignore rules are a safeguard, not a
substitute for that review.

## License

All rights reserved pending the project owner's choice of license. See `LICENSE`.
