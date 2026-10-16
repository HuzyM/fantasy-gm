# NHL schedules (FGM-005/006)

## PuckAPI real schedule observations

FGM-006 adds `--puckapi`, using the documented
[PuckAPI REST API](https://puckapi.com/docs) and its
[personal-project permission](https://puckapi.com/terms). No MCP connection or
Yahoo authentication is involved. The operator reports successful finished-CLI
acceptance for October 17–23 (47 games) and October 29–November 4 (48 games),
2026: the 32-team cohort, observed counts, DST conversion and back-to-back checks
passed. Both runs correctly retained `COVERAGE_UNVERIFIED` and exit 1. This is
human-reported acceptance of those observations, not proof of complete schedule
coverage. Automated validation remains synthetic and offline.

Run the following in a separate private PowerShell terminal, outside Codex or
an AI-observed terminal. The hidden prompt avoids putting the key in command
history; the environment key exists only in that shell and its child process.
Do not save it in a script, `.env`, profile, output file or chat.

```powershell
Set-Location 'D:\Codex\Fantasy GM\fantasy-gm'
$puckKey = Read-Host 'PuckAPI key (hidden)' -AsSecureString
try {
    $env:PUCKAPI_API_KEY = [System.Net.NetworkCredential]::new('', $puckKey).Password
    & .\.tools\bin\uv.exe run --locked --offline --cache-dir .tools/cache python -B -m fantasy_gm.schedule --puckapi --season 20262027 --from 2026-10-17 --to 2026-10-23 --limit 500 --view all
} finally {
    Remove-Item Env:\PUCKAPI_API_KEY -ErrorAction SilentlyContinue
    $puckKey.Dispose()
    Remove-Variable puckKey
}
```

`--offline` governs dependency resolution, not provider networking: this explicit
`--puckapi` command makes real requests. Each invocation normally costs six
credits: one `list_teams` request and one `get_games` request. Free credits are
finite; the application never buys credits or retries. A failed request may
still consume credits according to provider policy. Queries are spaced six
seconds apart and stop after at most two calls. Use each run intentionally.

Compare each team's observed count, opponents, home/away and start times with
the published NHL schedule. Check reported B2B pairs and context labels.
For a separate intentional Toronto DST check, replace the window with
`--from 2026-10-29 --to 2026-11-04`. Do not send credentials or response dumps to
Codex. A sanitized acceptance result is sufficient.

Supported options are `--game-type regular|preseason|playoff|all`, the existing
views and IANA display zones (Toronto by default). Dates remain inclusive,
1–31 days. A lower `--limit 1..500` can be selected. Requests include three
reported dates of padding at each end for candidate timezone/B2B context;
display filtering uses each verified instant in the requested zone.

Important interpretation:

- Counts are **observed**, not certified league totals. Coverage/date cutover and
  full schedule availability are not established by two matching weeks.
  `COVERAGE_UNVERIFIED` is deliberate; missing games/days are not proven zeros,
  and complete rankings/B2B absence are not claimed.
- A valid empty response means no games were returned, not that none were
  scheduled. Fewer than 500 results, HTTP success and matching sampled weeks
  do not qualify the coverage contract. Observed B2B pairs can be shown while
  the complete set of pairs remains unknown; "none observed" is not "none".
- The exact current 32-club code set qualifies the `20262027` cohort. Historical
  seasons do not inherit this qualification; missing catalogue identities fail
  safely rather than inventing historical mappings. Names are reported metadata.
- A result reaching the requested limit, or a declared count larger than the
  returned list, produces `POSSIBLY_TRUNCATED`. There is no automatic pagination,
  date splitting or extra spending. A smaller intentional window may be used.
- Only full ISO timestamps with explicit offsets become UTC instants. The docs
  also show time-only strings; these remain unplaced. Daily output includes the
  reported source date and UTC instant alongside the converted local time.
  Malformed offsets (for example, minute values above 59) also remain unplaced;
  they are not silently normalized into a different instant.
- FUT/LIVE/FINAL/OFF are supported states. Other states remain uncertain; no
  cancellation, postponement or rescheduling code is guessed. No history is
  inferred. Source data is an observation, not a real-time update guarantee.
- Exit 1 currently means an explicitly partial observation, including ordinary
  successful PuckAPI runs. Exit 2 means input/access failure; 401 becomes
  `AUTHENTICATION_FAILED`, 402 `CREDITS_EXHAUSTED`, 429 `RATE_LIMITED`. If the games
  request fails after catalogue retrieval, its code appears in the partial
  summary. No provider error text, response body or credential is printed.

The adapter owns its HTTP client, verifies TLS, ignores environment proxies,
rejects redirects/compression, clears cookies and suppresses request logging.
Responses are limited to 2 MiB, with bounded inactivity timeouts and a best-effort
90-second invocation deadline. Everything remains in memory. Yahoo integration
and disabled Yahoo-backed AI/MCP access are unchanged. The NHL-operated adapter
below remains disabled; it is not a fallback for PuckAPI errors.

## Preserved FGM-005 synthetic foundation

**FGM-005 is the offline foundation; direct NHL-operated access stays disabled.**
No subscription, API key, calendar download or Yahoo login is needed for the
synthetic demo. Every club/game in it is invented; it is not an NHL forecast.

```powershell
uv run --locked --offline python -m fantasy_gm.schedule --demo --season 20262027 --from 2026-11-01 --to 2026-11-07 --view counts
```

Use `--view opponents`, `--view back-to-backs`, `--view daily`, or `--view all`
(default). A seven-day explicit window is a weekly schedule; no Yahoo matchup
week is inferred. `--game-type regular|all` defaults to regular.
`--timezone America/Toronto` is the default; valid IANA zones are supported by
the locked tzdata dependency on Windows. Date windows are inclusive, 1-31 days.

Counts show scheduled, in-progress and completed observations, plus uncertainty.
All-team most/fewest rankings require a validated cohort and qualified complete
window coverage. Missing responses/dates never become known zeros. Back-to-back
indicators mean consecutive dates in the chosen display zone, with a day of
context on both edges. They do not measure rest hours, travel or lineup legality.
Timezone changes cannot reuse another zone's coverage qualification.

Back-to-back output groups consecutive-day games into numbered pairs and refers
back to shared games without repeating their details. Only games whose converted
local dates fall outside the requested window receive a context label. Equal
counts across every team produce one concise tie message.

## Offline acceptance and review

The human operator reported successful manual acceptance of the synthetic demo.
The subsequent CLI presentation cleanup has synthetic regressions for grouped
pairs, shared-game references, local-date context labels and equal-count ties.
This acceptance covers the offline demonstration, not real NHL integration.

The final locked offline suite passed 610 tests, with Ruff lint/formatting, strict
mypy, credential-pattern checks and whitespace checks passing. Independent
implementation review identified two issues, both corrected with regression
tests: overlapping windows must reconcile removed/replaced game IDs, and a
structurally valid catalogue must not certify the actual NHL cohort.

## Data flow and current gate

`providers.nhl.schedule` validates synthetic HTTP responses through an injected
exact `httpx.MockTransport`; `domain.schedule` holds immutable normalized data;
`sports.nhl.schedule` calculates reports without I/O; `fantasy_gm.schedule` renders
the standalone human CLI. The demo generates 32 fictitious clubs and exercises
the same adapter. Only its invented cohort and known synthetic date mapping
are qualified. The adapter leaves both NHL qualification flags false even when
a catalogue passes structural and season checks.

Constructing the adapter without a MockTransport is rejected before an HTTP
client exists. Passing a native or custom transport is also rejected. `--live`
always returns `ACCESS_NOT_ENABLED` with exit code 2, without creating a client
or sending a request. There is no environment variable that enables live use.
Complete synthetic count reports exit 0; partial reports exit 1; input/access
errors exit 2. No response bodies or arbitrary exception text enter errors.

The selected documented shape uses one `/schedule-calendar/{date}` response for
32 season-matching club IDs/codes and `/schedule/{date}` league windows. Actual
returned buckets drive advancement, not assumed seven-day jumps. Day and optional
root counts and repeated-date game memberships are reconciled; conflicts/errors
stop collection and retain earlier
validated observations as partial. Missing timestamps and unfamiliar type/state
codes stay uncertain. There is no per-team fan-out, fallback, retry or redirect.

The adapter bounds raw responses to 2 MiB, normalized games to 4,096, catalogue
entries to 64, requests to 12 and elapsed checks to a 90-second command budget.
Requests are sequential with a one-second minimum start interval and bounded
HTTP inactivity timeouts. Synchronous deadline checks are best effort, not hard
cancellation. TLS verification and environment-proxy isolation are configured;
all requests in this implementation use an in-process synthetic transport.

## Contracts that remain unverified

- Permitted automated use of the NHL-operated service remains unresolved.
- The exact timezone/cutover of source date buckets is not established. The
  adapter's two-date guard is a candidate test envelope, **not proof of coverage**;
  its snapshots always leave coverage qualification false.
- Catalogue/window availability, current-season coverage, explicit empty periods,
  timing, updates and real-world completeness need bounded human-operated live
  acceptance after source authorization. No live requests occurred in this task.
- The narrow published mappings are FUT/LIVE/FINAL/OFF and game types 1/2/3;
  unknown codes remain unknown. The domain can represent POSTPONED, CANCELLED and
  RESCHEDULED observations, but the NHL adapter does not guess codes for them.
  These exception states never enter ordinary game counts or confirmed B2Bs.
  No change history or replacement-game identity is inferred from a snapshot.

The [existing implementation plan](superpowers/plans/2026-10-16-fgm-005-nhl-schedule.md)
contains the public evidence and the remaining access/date questions. An
environment switch, a passing synthetic test or a library license cannot settle
those questions. No generic contract-verification framework was added.

## Privacy and boundaries

Yahoo modules, OAuth, credentials, league settings, rosters and MCP are untouched.
The command neither joins Yahoo information nor exposes it to AI. Schedules and
responses remain in memory; no data cache, database, indexing or background work
exists. No actual NHL/Yahoo response fixtures are included. Future projections,
player mappings, fantasy scoring, lineup optimization and transactions are out
of scope.
