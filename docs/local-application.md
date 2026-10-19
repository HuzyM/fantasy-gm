# Local application

Run from the repository root with Python 3.12+ and Node installed:

```powershell
uv sync --locked
cd frontend
npm ci
npm run build
cd ..
python -B -m fantasy_gm.web
```

Open `http://127.0.0.1:8765/`. Use `--port 8766` if the default port is busy.
Use the exact numeric host and port printed by the launcher. The built application
and API share this origin. The default run uses synthetic examples, does not load
environment credentials, and makes no provider requests. No browser extensions,
remote service or development server is required at runtime. Stop with Ctrl+C.

## Human-only private session

The owner approved an optional process-local private browser boundary. Agents,
AI-observed terminals, browser automation and MCP must never run this mode or
inspect its private session. Close these tools and disable recording, transcripts,
remote views and screen sharing before a human runs:

```powershell
python -B -m fantasy_gm.web --private --interactive
```

The existing Yahoo OAuth configuration is read only after interactive confirmation.
The existing hidden terminal OAuth flow performs one authorization exchange, then
at most four Fantasy GETs: league discovery, owned teams, league membership and one
selected owned team's roster. There are no refreshes, retries or browser OAuth
callbacks. No settings, manager details, standings, scores, statistics, news or
injury status are fetched. Existing terminal CLIs are unchanged.

Only the selected league display name/season and whitelisted roster fields reach
the browser. Opaque Yahoo player IDs remain Yahoo IDs: no name-based NHL identity,
photo, injury or statistics match is inferred. Reported positions and affiliations
remain unverified where the provider marks them so; returned counts never establish
roster completeness, reserve inclusion, lineup legality or effective coverage.

The launcher prints a browser link containing a random capability in its fragment.
The application removes the fragment immediately and retains the capability only
in JavaScript memory. API requests use an Authorization header. No capability,
tokens or private fields belong in browser storage, cookies, queries, screenshots,
fixtures, logs or saved files. Reloading the page loses the browser capability;
the human can reopen the launcher link while its session remains valid. Treat that
link as private. The process drops token references before serving; dropping Python
references is not a guarantee of physical memory erasure. Operating-system paging,
browser extensions, history synchronization and recording are outside this boundary.

The session expires 20 minutes after loading, using a monotonic clock. The server
clears its private display data and capability on expiry, disconnect or shutdown.
The browser clears its display when expiry is observed. There is no synthetic
fallback after a private session becomes unavailable. Disconnect is the sole local
POST operation and only discards local state; it makes no Yahoo write or revocation.

## Optional public schedule observation

A human may add `--public-schedule --interactive` to either launch mode. A separate
terminal confirmation approves one public PuckAPI load for today through six days
later in `America/Toronto`. It uses at most two existing provider requests, normally
six credits. Only the existing `PUCKAPI_API_KEY` configuration is used; no caller-
provided URLs or Yahoo identities are sent. There is no API-triggered refresh.
No live public or private provider request is part of automated verification.

The API reuses pure domain schedule analysis and roster-to-team joins. Missing
coverage remains unknown; observed counts are not verified totals; unplaced and
uncertain games and incomplete back-to-back coverage remain explicit. Team games
do not prove player appearances. A failed startup load ends the launch without
substituting a fabricated observation.

## Request boundary and verification

The server binds only `127.0.0.1`, rejects any other Host or Origin, rejects cross-
site and same-site fetch metadata, disables proxy headers, access logs and provider
tracebacks, and emits no-store, no-referrer, same-origin resource and content
security headers. No CORS, arbitrary proxy, browser credential input, persistence,
automation, MCP or provider-write route exists. Static files are restricted to
built web formats within `frontend/dist`; traversal, dotfiles, symlinks, Windows
junctions and source-map files are denied. Assets and API GETs never invoke a provider.

`GET /api/status` contains only mode and coarse connection/schedule states.
`GET /api/view` requires the capability in private mode. `POST /api/disconnect`
requires both capability and exact Origin. Other writes and all query strings are
rejected. Browser navigation uses fragments, so all eight screens share `/`.

Run the offline suites and checks:

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy
cd frontend
npm test
npm run build
```

On restricted Windows runners, asyncio's internal wakeup socket may require a
runner permission adjustment even though all provider network access is blocked
by test fixtures. This is not authorization for a private or live provider test.
