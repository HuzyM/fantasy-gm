# Local application

Run from the repository root with Python 3.12+ and Node installed:

```powershell
uv sync --locked
cd frontend
npm ci
npm run build
cd ..
uv run python -B -m fantasy_gm.web
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
uv run python -B -m fantasy_gm.web --private --interactive
```

The existing Yahoo OAuth configuration is read only after interactive confirmation.
The exact private confirmation is `APPROVE PRIVATE BROWSER`. A previously approved
engineering change or synthetic test run does not authorize this human session.
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

A human may add `--public-schedule --interactive` to either launch mode. Before
public consent, the terminal asks for a planning start in exact `YYYY-MM-DD` form.
Press Enter to retain the launcher's Toronto-today default, enter another date, or
type `CANCEL` to stop. The launcher displays the start and end: exactly seven
consecutive inclusive `America/Toronto` calendar dates, without Monday realignment
or a Yahoo matchup-week inference. Calendar arithmetic retains those dates across
both DST changes and month/year boundaries. For example, December 31 through
January 6 is valid within one season. Dates must remain within the July–June season
derived from the start; a private session must also match its discovered league
season. Missing/unsupported season or invalid date input ends startup before the
dependent public request; it does not silently choose another window.

A separate terminal confirmation then approves one public PuckAPI load for that
window. Read its request/cost explanation before typing `APPROVE PUBLIC SCHEDULE`.
It uses at most two existing provider requests, normally six credits at the
reviewed rates. This is an estimate, not a checked account balance. There is no
balance lookup, purchase, fan-out, automatic retry or refresh. Refusing consent
makes no dependent public request. Only the existing `PUCKAPI_API_KEY` configuration is used; no caller-
provided URLs or Yahoo identities are sent. There is no API-triggered refresh.
No live public or private provider request is part of automated verification.

The API reuses pure domain schedule analysis and roster-to-team joins. Missing
coverage remains unknown; observed counts are not verified totals; unplaced and
uncertain games and incomplete back-to-back coverage remain explicit. Team games
do not prove player appearances. A failed startup load ends the launch without
substituting a fabricated observation.

Private Yahoo-only mode also asks for the planning start and retains the same
explicit window while schedule observations and schedule-derived opportunities
remain unavailable. Public schedule-only mode supplies no owned roster. Neither
mode borrows synthetic observations or establishes acceptance of the full journey.

In Planner, review the exact planning dates and timezone, then inspect Daily
matchups or the existing Roster week matrix. Compare players opens the same
displayed seven-date window; observed-player Comparison defaults to Schedule.
Zero or one returned player cannot create a comparison pair. Performance, injury
reports and confirmed appearances remain unavailable without their own sources.
Date/week controls only browse the observations already held in memory. Chosen
non-Monday starts stay exact in observed mode; unloaded dates stay unknown and
an empty observation is not a confirmed off-day. Return to Loaded window (or the
Yahoo-only planning window) to review the launcher's original dates. To load a
different public window, stop and start a new human launcher session, choose its
start and separately confirm the load. Browser assets, local API reads, browsing
and comparisons make no provider request.

## Context reviews and manual plan

Start with **My Roster** and inspect a returned player, then choose **Prepare roster
review**. In Planner, select a date and **Planner review player**, then **Prepare
Planner review**. Both paths prefill the exact returned identity and date; a
verification task needs no supported game association. The action remains yours
to enter. Review and edit the factual starting reason before adding the item.

Observed-player comparison opens on **Schedule**. Select two distinct returned
players and a **Comparison review date**, then **Prepare comparison review** to
record both exact references, the date and original planning window. **Reopen
review context** or **Reopen comparison context** returns to the item's exact
player or ordered pair, date and window. Pair swaps, search, filters and navigation
do not change an existing item. An empty or single-player roster cannot create a
comparison item. Unavailable performance and competition data do not supply plan
reasons; the offline demo remains separate from observed planning.

The referenced observation qualifications remain visible separately from your
editable action and reason. Partial/missing coverage, source issues, excluded or
disputed games and unplaced observations remain limitations after acknowledgement.
Shared dates are review prompts, not slot-capacity conflicts. Back-to-back
opportunities do not confirm appearances or goalie starts. Context preparation is
unavailable for a different displayed weekly window, including an overlapping
window: return to the loaded window or perform a new separately confirmed human
launcher load. No browsing or plan action makes a provider request.

In Schedule Planner, open **Manual plan**. Read its lifetime and source limits
before entering anything. With an owned Yahoo roster loaded, choose a returned
player (the exact returned reference distinguishes matching names), a review date
inside the launcher's planning window, your review action and your reason. Add the
item, then use Edit, Mark reviewed/Return to pending, Remove or Reopen player
context. Editing an item returns it to pending. Reopening shows the same returned
reference on the player's profile; it does not resolve that Yahoo identity to an
NHL athlete. Filtering/sorting, profile navigation and browsing other displayed
weeks retain saved items and their original dates. The form always uses the
original loaded planning window; browsing an unloaded week does not rebind items
or create a game. In-progress form edits are discarded when the panel closes or
the screen changes; added items remain mounted until the session ends.

This is a manager-authored review list, not lineup assignment, slot validation,
start/sit advice or an operation sent to Yahoo. Reviewed means only human
acknowledgement, never a source verification or completed Yahoo change. Yahoo-only
players and unavailable affiliations can receive verification tasks without a
game. Schedule coverage, reported slots/affiliations and player appearances retain
their limitations after acknowledgement. **Record no action needed** is a valid
review outcome even with no items; any pending items remain visible and need their
own acknowledgement. No minimum item count is required. Public schedule-only use
has no owned roster and cannot record a manual plan or no-action acknowledgement.

Items and review acknowledgement live only in the mounted page. Nothing is saved
to the server, browser storage, cookies, URL/history payloads, exports or telemetry.
Navigation and plan controls request no provider. Complete your work within the
existing 20-minute private lifetime; plan interaction cannot extend it. Reload
loses the plan and browser capability. Reopening a still-valid launcher link may
reload observations but never restores lost items. Disconnect, observed expiry or
lock, source/session replacement and server restart discard private items and
acknowledgement; Back/Forward cannot recover them. Clearing occurs when browser
unavailability is observed, without promises about a suspended browser or physical
memory erasure. Make any chosen provider changes manually in Yahoo.

Synthetic verification cannot establish live provider compatibility, human
correctness, usefulness or full v1.0 acceptance. Any private
correctness/usefulness session still needs separate authorization and the human-only
privacy precautions above; do not share private observations, screenshots or links
with AI/recording tools. Existing session expiry, reload loss and clearing rules
continue to apply.

## Human release acceptance runbook

This is an instruction for a future separately authorized human operation, not
permission to run it now. The [release-candidate record](release-acceptance.md)
identifies the exact runtime revision and independent engineering gates. Human
correctness and usefulness remain pending until actually performed. Do not launch
private mode through an agent or ask an agent to watch or inspect its output.

1. Obtain the owner's explicit authorization for the particular human sessions,
   chosen windows and total request budget before beginning. Each private launch
   is bounded to one authorization exchange and at most four Fantasy GETs
   (discovery, owned teams, membership and one selected owned roster). Each
   separately approved public window adds at most two existing PuckAPI requests,
   normally six credits at reviewed rates. A new launch, alternate window or
   failure recovery needs authorization within that total budget; three usefulness
   sessions are not covered by a single launch approval. Use existing free-tier
   access only. Do not use paid/trial access, query accounts/balances, buy credits,
   retry or enable automatic refresh. Stop if the approved access or budget is
   unavailable; the cost estimate is not a checked balance.
2. Close AI/MCP observation, automated browsers, recording/transcription, remote
   views and screen sharing. Use a private human terminal and browser. Keep these
   tools closed throughout source reconciliation and planning. Do not save a
   transcript, screenshot, provider response, private plan or private report.
3. Use the engineering-verified candidate and built frontend. For the complete
   journey, the human runs from the repository root:

   ```powershell
   uv run python -B -m fantasy_gm.web --private --public-schedule --interactive
   ```

   Read the private consent text, authenticate through the existing hidden
   terminal flow and select only the intended discovered league and owned team.
   Choose a start in `YYYY-MM-DD` form, including a deliberate nondefault start
   when checking window selection. Confirm the displayed start/end are exactly
   seven inclusive America/Toronto dates, then separately approve the explained
   public schedule cost. Use `CANCEL` to stop if any selection or cost is wrong.
   Rejection, unsupported responses and exhausted credits must remain sanitized;
   do not try again without remaining explicit authorization. Yahoo-only and
   schedule-only modes remain useful degraded modes, but cannot accept the full
   release journey.
4. Open only the printed numeric-loopback browser link and keep it private. After
   loads finish, start the review timer for a usefulness session. In **My Roster**,
   privately reconcile the selected team and returned fields against the owner's
   Yahoo page. Distinguish returned entries from a complete roster, eligibility
   from assigned slots, and reported affiliation from verified NHL identity.
   Do not export data, inspect network payloads or capture credentials to do this.
5. In **Schedule Planner**, confirm the original dates/timezone, inspect **Daily
   matchups** and **Roster week**, and privately compare representative displayed
   games with their source: opponent, home/away, local start time and state where
   available. Check the qualifications for excluded/disputed games, missing times,
   unverified affiliations and partial/unloaded coverage. No qualifying game
   observed is not proof of an off-day; team games do not prove appearances.
   Sample agreement does not certify complete coverage or roster/rule semantics.
6. Use **Prepare roster review**, **Prepare Planner review** or **Prepare comparison
   review** and the **Manual plan** controls described above. Confirm the exact
   returned identity or ordered pair, date and original planning window after
   adding/reopening an item, navigating, filtering or swapping the comparison.
   Check Edit, Mark reviewed/Return to pending and Remove using only the current
   in-memory plan. A verification action for an unsupported affiliation needs no
   invented game. **Record no action needed** is valid without a minimum item
   count. Unknown data stays unknown and reviewed means acknowledgement only.
   Make any chosen real changes manually in Yahoo; the plan never sends them.
7. Finish the review timer when the intended review list or no-action outcome is
   ready. Each of three sessions must finish within ten minutes after loads, with
   reduced effort reported in at least two sessions and zero unsupported claims
   of completeness, player participation, lineup legality or scoring advantage.
   A mismatch affecting a claimed fact blocks correctness acceptance until
   corrected or accurately represented as disputed/unavailable. A failed
   usefulness gate requires product reconsideration; do not invent success.
8. After timing, check relevant lifecycle behavior within the separately approved
   launches: reload loses capability and plan; reopening a still-valid launcher
   link may reload observations but restores no plan. Disconnect clears the local
   session; a server restart cannot restore it. Where authorized, observe the
   existing 20-minute expiry rather than extending it with planning. After browser
   unavailability is observed, revisit history and visibly reopen any available
   plan/navigation region before checking old items are absent; a closed panel
   alone does not prove clearing. Source/session replacement cannot restore old
   items. Do not authorize another provider load just to exercise these cases;
   arrange any needed separate launches explicitly. Clearing is observed browser
   behavior, not a guarantee for suspended browsers or physical memory erasure.
9. Stop the launcher and close private pages before reconnecting observation
   tools. Share only the coarse fields below. Do not send account/roster/plan
   fields, private counts or structural details, player references, dates, window
   choices, links/capabilities, tokens, screenshots or provider bodies to an AI
   tool or issue. Add no telemetry or saved private acceptance dataset.

The only shareable acceptance report is a coarse summary such as:

```text
Human source correctness: PASS / FAIL / NOT PERFORMED
Relevant session clearing: PASS / FAIL / NOT PERFORMED
Session 1: PASS / FAIL / NOT PERFORMED; review duration: __; reduced effort: YES / NO / NOT ASSESSED
Session 2: PASS / FAIL / NOT PERFORMED; review duration: __; reduced effort: YES / NO / NOT ASSESSED
Session 3: PASS / FAIL / NOT PERFORMED; review duration: __; reduced effort: YES / NO / NOT ASSESSED
Zero unsupported claims: PASS / FAIL / NOT ASSESSED
```

Do not fill this with expected results. A private failure can be reported simply
as FAIL; no private reproduction detail is needed. Keep the release unaccepted
and #30/#26 open while any required result is pending or failed. Personal local
acceptance does not clear provider/asset rights for public distribution; see the
[distribution gate](release-acceptance.md#release-decision-and-rights).

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
uv run pytest
uv run ruff check src tests
uv run mypy
cd frontend
npm test
npm run build
```

On restricted Windows runners, asyncio's internal wakeup socket may require a
runner permission adjustment even though all provider network access is blocked
by test fixtures. This is not authorization for a private or live provider test.
