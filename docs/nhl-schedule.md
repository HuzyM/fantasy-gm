# NHL schedule foundation (FGM-005)

**Offline implementation only. Live NHL integration has not been accepted.**
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
