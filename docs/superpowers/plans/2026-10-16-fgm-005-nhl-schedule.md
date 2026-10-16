# FGM-005 NHL Schedule Intelligence Implementation Plan

**Execution amendment (2026-10-16):** The subsequent user instruction explicitly
approves offline implementation on feature/fgm-005-nhl-schedule-foundation while
the source gate remains unresolved. It supersedes this document's earlier
instruction to block all implementation on stage 1. No live access, commit,
push or PR is authorized. A labelled synthetic demo is now required. See
docs/nhl-schedule.md for the implemented boundaries; the public evidence below
is preserved as the planning record. Transport injection accepts MockTransport
only; no live-enabling flag exists. Coverage now records its qualified timezone
so it cannot be reused after a timezone change. Domain exception states do not
imply that the NHL adapter recognizes undocumented codes.

**Offline checkpoints:** Models/calculations, synthetic-transport adapter and
standalone demo CLI are implemented. Independent code review identified two P2
issues: inconsistent repeated-date game membership and premature cohort
qualification. Both have regression tests demonstrated failing before correction
and passing afterwards. The adapter now reconciles overlapping bucket membership
and leaves both source qualification flags false; only the synthetic demo
qualifies its invented cohort/date profile. No live acceptance is claimed.

> **For agentic workers:** After implementation approval, use superpowers:executing-plans task by task. This revision authorizes no implementation, dependency installation, branch, live endpoint request, commit or publication.

**Goal:** Automatically show NHL-wide game counts, opponents, home/away games and back-to-back indicators for explicit date windows, without Yahoo login or a paid subscription.

**Architecture:** One small NHL adapter -> immutable provider-independent models -> pure schedule analysis -> standalone human CLI. Reuse existing httpx; add only the approved tzdata dependency during implementation.

**Tech stack:** Python 3.12+, existing Pydantic/httpx/pytest/Ruff/mypy, datetime/zoneinfo/argparse, approved tzdata.

**Spec:** Sections 1-6 define the revised engineering specification; sections 7-8 define execution and acceptance. Revised 2026-10-16, replacing the previous manual-input and selected-team designs in this same file.

## Global constraints

- Planning only; preserve main at `beb525723c43466c2a7e09d61ffc73c3ad8ef2b8` during this task.
- No paid API, subscription, paid trial or purchase. No manual calendar/CSV import, parser, upload or download workflow, including as fallback. No PDF/OCR.
- No live NHL endpoint requests during planning. Evidence is published documentation and public implementation source, not tested live contracts.
- Preserve Yahoo OAuth, read-only league/roster functionality, in-memory handling and all privacy restrictions. Keep YAHOO_AI_TOOLS_ENABLED=false by default and Yahoo-backed MCP access disabled. No Yahoo imports, joins or requests in this workflow.
- No database, persistent cache, polling, provider registry, frontend, generic transport refactor, player mapping, projections, optimization, transactions or AI integration.
- One source and one human-triggered in-memory observation per invocation. No fallback provider or franchise-history framework. Synthetic fixtures only; no captured bodies, credentials or Yahoo data in tests/logs/Git.
- Architecture approval and the zero-cost preference do not resolve the source-access question. Real endpoint access still requires that decision and separately approved live acceptance.

## Review focus

1. Missing buckets, empty responses and incomplete club catalogues must not become proven zeros or NHL-wide rankings (stages 2-3).
2. UTC midnight, DST and query-edge context must not omit games or fabricate negative B2B results (stages 2-3).
3. Unknown states, missing timestamps and schedule changes must remain visible uncertainty (stages 2-4).
4. Conflicting game IDs, season mismatches and historical clubs must not establish false all-32 coverage (stages 2-3).
5. Denial, transport failures and request caps must stop requests and preserve honest partial output and Yahoo isolation (stages 3-5).

## 1. Source decision: direct NHL, no paid service

**Selected technical direction:** NHL-operated `https://api-web.nhle.com/v1/`, with existing httpx and one small adapter. Public clients describe requests without a subscription/API key. This is a zero-subscription design, not a guarantee of indefinite free access or an officially supported external developer API.

**Confidence after the 2026-10-16 public-documentation follow-up:** High as a technical candidate; the catalogue fields, league-window shape and explicit empty-day representation are now corroborated by published client documentation/source and historical examples. Permitted automated use, source-date timezone semantics and current operational guarantees remain unresolved. No live endpoint has been tested here.

NHL terms restrict unauthorized automated collection; permission for this integration remains unresolved. [NHL terms, sections 2 and 7](https://www.nhl.com/info/terms-of-service).

The smallest remaining access step is identifying applicable published permission or obtaining NHL clarification covering limited personal automated requests and local analysis. The operator controls any contact; do not contact NHL or accept terms on their behalf. This is an evidence question, not a determination that every use is prohibited. Neither an open-source client license nor absence of an API key resolves it. No paid substitute is selected.

### Alternatives checked and excluded

Research date: 2026-10-16. These findings explain the source decision; they do not add adapters.

| Source | Current evidence | Decision |
|---|---|---|
| Direct NHL | Public clients describe league and club schedules without keys/subscriptions. External API SLA, applicable permission and quota not established. | Preferred zero-cost direction, subject to source qualification. |
| BALLDONTLIE NHL | Free tier has teams/players, not Games; Games require ALL-STAR, currently US$9.99/month, 60 requests/minute. API terms cover personal analytics/fantasy uses under their conditions. | Excluded by no-payment requirement; a trial is not a sustainable free route. |
| API-SPORTS Hockey | Lists NHL and advertises 100 free requests/day. Current-season NHL entitlement on that tier remains unverified; terms leave relevant data-use permissions to customers. | No confirmed equivalent free coverage or resolved permission advantage; not selected. |
| SportsDataIO DiscoveryLab | Advertises free last-season NHL data, paid current/live upgrade. | Does not satisfy upcoming-schedule needs at zero cost. |

Sources: [BALLDONTLIE NHL pricing/access](https://nhl.balldontlie.io/), [API terms](https://www.balldontlie.io/terms.html), [API-SPORTS Hockey](https://api-sports.io/sports/hockey), [terms](https://api-sports.io/terms), [DiscoveryLab NHL](https://discoverylab.sportsdata.io/personal-use-apis/nhl). Provider permission is not a claim of NHL endorsement. No account, trial, purchase or data API call was made.

No NHL library is needed: it uses the same upstream and still needs our validation/bounds. Large dataframe/archive packages add unnecessary dependencies.

## 2. Endpoint evidence and choice

Labels: **R** repository verified; **D** described/implemented by linked authors, untested here; **U** unresolved; **P** application proposal. Community references establish their clients' behavior, not NHL guarantees.

| Endpoint | D: described coverage | Choice / unresolved points |
|---|---|---|
| `/schedule/{date}` | League window with gameWeek[], dated games[], numberOfGames and navigation dates. Published examples include seven consecutive explicit empty days. | Preferred: a few windows rather than 32 club requests. Use actual returned dates and counts; never assume one-day responses or fixed stepping. Current behavior still needs acceptance. |
| `/club-schedule-season/{team}/{season}` | Flat games[] for one club/season. | Viable different design but 32 calls and duplicate shared games. Not implemented as a fallback. |
| `/club-schedule/{team}/week/{date}` | One club's weekly schedule. | All-team fan-out and unqualified week anchoring make it less suitable. Not selected. |
| `/schedule-calendar/{date}` | Public client docs explicitly describe all 32 teams; teams[].id, seasonId and abbrev are corroborated by fastRhockey's published contract. | Selected metadata route. Validate each entry's season and identity and the current cohort at runtime; do not derive idle clubs from games. Same source, not another provider. |

Evidence: [nhl-api-py schedule docs](https://github.com/coreyjs/nhl-api-py/blob/d6a9cb532ce58b5d0312fea2ca785f442aa4c2b6/docs/schedule.md), [client implementation](https://github.com/coreyjs/nhl-api-py/blob/d6a9cb532ce58b5d0312fea2ca785f442aa4c2b6/nhlpy/api/schedule.py), [NHL-API-Reference](https://github.com/Zmalski/NHL-API-Reference/blob/20d3f0e1a3528fb4d5cfdb7018d416cbd6a89f40/README.md), [author's exploration notes](https://github.com/matsonj/nba-box-scores/blob/main/docs/nhl-api-reference.md).

**D:** game id, season, gameType, homeTeam/awayTeam IDs and abbreviations, startTimeUTC, gameState, gameScheduleState and dated buckets. Treat IDs as opaque; never decode season/type from them. Candidate types: 1 exhibition, 2 regular, 3 postseason. Candidate states: FUT scheduled, LIVE in progress, FINAL/OFF completed. OK is the narrow normal gameScheduleState candidate.

**U:** exhaustive states, PRE/CRIT meaning, exact postponed/cancelled codes, reschedule ID continuity, freshness, truncation, empty-period and pagination guarantees. Speculative PPD/CNCL examples are not supported mappings. A current snapshot cannot prove a schedule changed, explain a missing game or establish change history. Do not infer cancellation from absence or a makeup date from an exceptional record's timestamp.

Retain reported bucket dates separately from UTC instants. Their calendar convention still needs qualification; they are not Yahoo scoring dates. Unknown types stay unknown. Additional corroboration: [sportsdataverse schema](https://github.com/sportsdataverse/sportsdataverse-py/blob/4636718a57a2380a5c9527d8d8b82048f00f5372/tools/codegen/schemas/native/nhl_api_web/club_schedule_season.yaml), [parser](https://github.com/sportsdataverse/sportsdataverse-py/blob/4636718a57a2380a5c9527d8d8b82048f00f5372/sportsdataverse/nhl/nhl_api_web_parsers.py).

### Public-documentation follow-up: resolved contracts and precise gaps

This is a bounded documentation investigation, not a live contract test. Official NHL terms/contact information and schedule announcements were checked alongside the authors' own client docs/source. No general NHL developer permission grant, quota, completeness SLA or exhaustive state specification was located. This is a search result, not proof that no agreement exists. Third-party API directories, robots/CORS behavior and unrelated sites using the NHL name are not permission evidence.

| Question | Public evidence now establishes | Remaining qualification |
|---|---|---|
| All-team catalogue | nhl-api-py explicitly describes all 32 clubs. fastRhockey documents integer id/seasonId and abbreviation, plus optional localized names. | Require exactly 32 unique current-scope clubs, each seasonId matching the explicit season, consistent with game identities. A future different cohort is unsupported, not coerced. This is a documented profile; current results are untested. |
| Window and empty dates | The published historical NHL_GIT_LAB example has seven dated buckets, each numberOfGames=0 with games=[], including an offseason period. nhl-api-py describes a week starting at the requested date and extracts daily results by matching the returned date. | Validate actual dates. Missing games, a missing bucket or an empty gameWeek is not an explicit empty day. A historical example does not promise today's offseason behavior. |
| Count consistency | Published window examples contain per-day numberOfGames and a top-level total. | Proposed safeguard: require nonnegative integer day counts equal to distinct validated games for that day; if a top-level total exists, reconcile it before filtering. Mismatches make coverage partial. Do not copy the wrapper's recalculated count as source evidence. |
| Identity and timing | Independent published schemas/examples contain game IDs, home/away identities, season/type and UTC kickoff fields. | IDs remain opaque. UTC conversion is specified; the exact timezone/cutover behind league bucket dates is not established. Eastern-time labels on human schedule pages do not prove API bucket semantics. |
| Navigation and pagination | Examples supply adjacent start dates; the reviewed weekly client makes one request and returns its window without a page cursor loop. | No documented pagination/truncation guarantee. Continue by missing returned dates within our budget, never by treating navigation gaps as empty. Consistent counts only detect some omissions. |
| Exceptional states and updates | The narrow normal-state profile above is corroborated; published notes explicitly describe other codes speculatively. | No verified exhaustive cancellation/postponement vocabulary, ID continuity rule, update latency or change history. Unknowns remain uncertainty; a snapshot cannot establish a reschedule event. |

Evidence: [nhl-api-py catalogue/window documentation](https://github.com/coreyjs/nhl-api-py/blob/d6a9cb532ce58b5d0312fea2ca785f442aa4c2b6/docs/schedule.md), [its untransformed weekly and transformed daily implementations](https://github.com/coreyjs/nhl-api-py/blob/d6a9cb532ce58b5d0312fea2ca785f442aa4c2b6/nhlpy/api/schedule.py), [fastRhockey catalogue source/contract](https://rdrr.io/cran/fastRhockey/src/R/nhl_schedule_calendar.R), [author-published historical response examples](https://github.com/kendalga23/NHL_GIT_LAB/blob/master/new-api.md). Examples stay at their published sources; no response fixture is copied into this repository.

**Concrete request sequence, after access approval:** One schedule-calendar request for the explicit display start date, followed by schedule windows starting at the earliest uncovered required source date. Parse catalogue id/seasonId/abbrev, optional name.default; parse gameWeek[].date/numberOfGames/games and the previously listed game fields. No team-by-team fan-out is necessary for the documented route. Counts are source-relative coverage claims only, never proof that upstream omitted nothing.

**Two essential blockers remain:** (1) applicable automated-access permission; (2) a reliable definition of source bucket date/timezone boundaries sufficient to map every requested local-time instant to a bounded set of source dates. Public examples narrow the second issue but do not establish a universal rule. Do not erase either blocker by changing a boolean. Current cohort/empty-window/count behavior is a later bounded acceptance check; exceptional-state history can remain an explicit supported-feature limitation.

**Smallest next step:** The operator can use the [official NHL contact page](https://www.nhl.com/info/contact-us) for clarification. Ask whether limited unauthenticated GETs to the two schedule routes are permitted for a personal, noncommercial local CLI, with no redistribution, persistent response storage or polling; request applicable usage limits and published date/coverage documentation. No form was submitted and no third party was contacted. No fee, subscription or paid alternative is proposed. If permission is established but date semantics remain undocumented, a separately approved bounded human-operated acceptance session is the next evidence step; spot checks do not create an upstream completeness guarantee.

## 3. Architecture, files and contracts (P)

**R:** Existing frozen/strict Pydantic models, hidden validation inputs, httpx streaming/MockTransport and network-blocked tests fit this work. Existing domain.team.Team is a fantasy team requiring a league ID; do not reuse it for professional clubs. sports/nhl is a placeholder. Reuse Yahoo transport patterns without its XML helpers or a generic transport extraction. tzdata is not currently a runtime dependency; add it only during approved implementation for portable IANA data. [Python zoneinfo](https://docs.python.org/3.12/library/zoneinfo.html).

| File | Responsibility |
|---|---|
| src/fantasy_gm/domain/schedule.py | Frozen identities, games, snapshot coverage and reports. |
| src/fantasy_gm/providers/nhl/__init__.py and schedule.py | Fixed-origin bounded HTTP, consumed-field JSON parsing and window collection. |
| src/fantasy_gm/sports/nhl/schedule.py | Pure filtering, counts, ranking eligibility and B2B indicators. |
| src/fantasy_gm/schedule.py | Standalone argparse CLI and escaped human output. |
| tests/test_nhl_schedule.py | Synthetic adapter/transport/coverage tests. |
| tests/test_schedule_analysis.py | Pure analysis/timezone tests. |
| tests/test_schedule_cli.py | CLI, partial output and Yahoo isolation. |
| pyproject.toml and uv.lock | Approved tzdata only. |
| README.md, docs/architecture.md, docs/nhl-schedule.md | Usage, source basis, semantics and limitations. |

Five small models; use strict frozen configuration with hidden input values in errors:

- `ScheduleTeam(provider: str, provider_team_id: str, abbreviation: str, name: str | None)`: club identity, no Yahoo/franchise-history crosswalk.
- `ScheduledGame(provider_game_id: str, season: str, game_type: GameType, game_type_code: str, home: ScheduleTeam, away: ScheduleTeam, reported_date: date, start_time_utc: datetime | None, state: GameState, state_code: str | None, schedule_state_code: str | None, schedule_normal: bool)`. GameType=EXHIBITION/REGULAR/POSTSEASON/UNKNOWN; GameState=SCHEDULED/IN_PROGRESS/COMPLETED/UNKNOWN. UTC must be aware; missing is never midnight. Preserve bounded original codes.
- `ScheduleSnapshot(season: str, teams: tuple[ScheduleTeam, ...], games: tuple[ScheduledGame, ...], covered_dates: frozenset[date], cohort_verified: bool, coverage_contract_verified: bool, issues: tuple[str, ...], observed_at_utc: datetime)`. Covered dates mean validated source buckets, not completeness by themselves. Qualification reflects documented source evidence plus runtime validation, never an arbitrary CLI override. No raw JSON/URLs/HTTP objects in models.
- `TeamScheduleSummary(team: ScheduleTeam, scheduled: int, in_progress: int, completed: int, uncertain_dated: int, unplaced: int, back_to_back_pairs: tuple[tuple[str, str], ...], count_complete: bool, back_to_back_complete: bool)`. IDs form pairs. Completeness is relative to qualified source/window scope, not guaranteed real-world truth.
- `ScheduleReport(summaries: tuple[TeamScheduleSummary, ...], ranking_available: bool, issues: tuple[str, ...])`. Issues use fixed codes from section 6; no diagnostics framework.

Intended interfaces:

```python
# providers/nhl/schedule.py
NhlScheduleClient(http_client: httpx.Client)
NhlScheduleClient.get_schedule(*, season: str, start: date, end: date,
                              timezone: ZoneInfo, deadline: float
                              ) -> ScheduleSnapshot
# Parsing helpers remain internal. Stage 1 must settle the actual catalogue
# profile and source-date envelope before their fixtures are written.

# sports/nhl/schedule.py
analyze_schedule(snapshot: ScheduleSnapshot, *, start: date, end: date,
                 timezone: ZoneInfo, game_type: GameType | None
                 ) -> ScheduleReport
# None selects all known types; UNKNOWN remains uncertain.

# schedule.py
main() -> int
```

No ABC/Protocol/registry or second provider. Pure analysis has no I/O, clock or environment reads.

## 4. Acquisition, normalization and completeness (P)

Scope: all 32 current NHL clubs, one explicit season, 1-31 inclusive local days. No historical cohort/expansion support by silently reusing today's clubs. Hardcoded 82/84-games checks do not establish completeness.

1. Validate dates/season/ZoneInfo before I/O. Convert the display interval plus one local day of B2B context each side into UTC boundaries using calendar-day arithmetic, not fixed 24-hour shifts.
2. Establish the season-specific club cohort from the documented catalogue profile: unique positive IDs, unique codes, every seasonId matching selected scope and the expected current cohort. Exactly 32 arbitrary/historical clubs is insufficient. Never derive the cohort only from games in the window. Missing metadata permits partial observed-team lists, not NHL-wide rankings.
3. Determine required source buckets using the qualified source-date/UTC relationship. Padding by an arbitrary number of days is not proof. Stage 1 must pin a bounded mapping/envelope covering all requested instants and context. If unqualified, coverage stays unverified; no open-ended crawl.
4. Request league windows sequentially from the earliest required uncovered bucket. Validate actual dates, explicit games collections and nonnegative integer day numberOfGames against distinct validated games before type/date filtering; reconcile the optional root total. Accumulate covered dates, deduplicate games. Never follow returned URLs, blindly step seven days or interpret omitted dates/navigation as empty days.
5. Stop when covered, on no progress, a structural/transport error, or request/time budget. Duplicate buckets must reconcile; missing/truncated/inconsistent data is partial. Retain prior validated observations but never mark missing/unattempted periods empty. No alternate endpoint fallback.
6. Analyze/display/discard the in-memory observation. Acquisition time is not a freshness guarantee and sequential windows are not atomic.

### Required normalization

Require UTF-8 JSON objects and explicitly typed collections. Reject duplicate JSON keys, NaN/Infinity, booleans/floats/nonpositive IDs and required-field coercion. Bound consumed strings/codes; ignore unrelated presentation fields without retaining bodies. IDs become exact strings. Validate distinct home/away IDs/codes and consistent catalogue mappings; never join by names. Required identity/date/season errors invalidate the affected window rather than silently dropping a record.

Season is eight ASCII digits with consecutive start/end years; dates round-trip YYYY-MM-DD, start<=end. Club codes must match [A-Z]{3}; no URLs, aliases or path fragments. Per-game season must match selected scope; other-season context cannot establish selected-season coverage. Consumed gameType must be an integer, excluding bool; unfamiliar integers normalize UNKNOWN.

Identical normalized game IDs collapse. Conflicting date/time/teams/season/type/state for one ID invalidates affected coverage; do not choose a winner or double-count. Different IDs remain distinct observations; no heuristic reschedule merge. A later-window conflict produces partial output, not an automatic retry.

Missing/invalid optional timestamp/status retains an identifiable uncertain record where safe. Never substitute the clock or reported date for a kickoff instant; never attach a timezone to a floating time by assumption. Normalize trustworthy aware instants to UTC.

### Counts and ranking

Default regular-season filtering excludes known exhibition/postseason, but unknown types remain uncertain because inclusion cannot be decided. All-types mode includes all known types, with UNKNOWN still uncertain. Normal counts require usable instant, mapped state, supported selected type and schedule_normal=true. Show scheduled/in-progress/completed separately and their sum as window total; uncertain/exceptional records never silently join normal counts.

Ranking requires a qualified current cohort/date mapping, every display bucket covered, valid records, consistent duplicates and no uncertainty that could change counts. B2B completeness additionally requires adjacent-day context. Missing context alone need not block otherwise complete window counts. Unknown/unplaced records may be scoped out only when qualified date mapping proves they cannot affect the display interval.

An idle team's zero is source-relative confirmed only under those count-coverage gates. Otherwise show `0 observed; total unknown`. Partial lists are alphabetical, with no winner/most-games claim; never rank just successful teams as if all clubs were compared. Missing catalogue can still permit safe observed-team listings.

## 5. Time, states and human CLI (P)

Default display/filter zone America/Toronto; allow a valid IANA override. Filter by converted local date, retain UTC and print numeric offset. No host timezone, fixed Eastern offset or silent UTC fallback on missing zone data.

B2B means games on consecutive converted dates in the selected display zone, explicitly labelled. It is not an official rest-hours/travel/Yahoo-week rule. Analyze adjacent-day context before trimming, include pairs with either member in the display interval and label outside-range neighbors. Same-day games alone are not pairs; deterministic distinct-ID pairs handle multiple games per date without assuming a one-game rule. Unknown/exceptional games do not establish confirmed pairs. Missing context/uncertainty means `none observed; completeness unknown`, not `no back-to-backs`.

Display postponed/cancelled only when reliable mappings and acceptance establish them. Otherwise show unknown/exceptional state with bounded escaped NHL codes. A fresh date is the presently reported date, not proof of reschedule history. This limitation explicitly constrains the schedule-changes question.

Proposed command, after approval and implementation (not executed here):

```text
uv run --locked python -m fantasy_gm.schedule --live --season 20262027 --from 2026-10-19 --to 2026-10-25
```

Require explicit season/from/to, --live for network intent, default regular filtering. Optional --timezone and --game-type regular|all. Help/input errors cause no requests. All current clubs are queried; no Yahoo login, implicit fantasy week, player recommendation or manual-input mode. --live is operator intent, not provider permission; do not enable it before source qualification.

Output source/season, zone, acquisition time and coverage; all-club table when qualified; dated opponents/home-away/state and B2B indicators; uncertainty and limitations. Complete rankings sort by total descending then club code. Escape control characters in source strings. Exit 0 for source-relative complete window counts, 2 for input/access errors, 1 for unavailable/partial results. Independently incomplete B2B/history reporting stays labelled even when it cannot affect complete counts.

## 6. Transport and isolation safeguards (P)

- Fixed HTTPS api-web.nhle.com origin, GET only, validated dates and the two selected path patterns. No arbitrary URLs, players/rosters, returned-link following or hidden fan-out.
- Dedicated existing-httpx client: TLS verified, trust_env=False, no inherited auth/cookies/hooks, redirects or automatic retries. No credential inspection. Request JSON/identity encoding; reject compressed bodies.
- Stream raw bytes <=2 MiB/response regardless of Content-Length. Bound invocation to 4,096 games and 64 catalogue entries, consumed strings <=256 chars, codes <=32. These are product limits, not NHL maxima; overflow is explicit, never truncated.
- At most 12 sequential requests including metadata, >=1 second between starts. Self-imposed provisional limits, subordinate to authorized quotas; no polling.
- Absolute monotonic command deadline 90s, passed into every fetch; per-fetch deadline min(command deadline, fetch start+30s). Connect/read/write/pool caps 3/5/5/2s, each limited by remaining budget. Check before/after spacing, after headers, during chunks and before return. Synchronous elapsed checks are best effort, not hard cancellation of DNS/slow headers.
- Denial/rate limit, transport error, unavailable response, deadline, malformed required data or no progress stops further requests. Preserve prior safe observations as partial; no retries or evasion.
- Fixed errors/issues: ACCESS_NOT_ENABLED, INPUT_ERROR, REQUEST_REJECTED, RATE_LIMITED, TIMEOUT, TRANSPORT_ERROR, RESPONSE_TOO_LARGE, INVALID_RESPONSE, UNSUPPORTED_RESPONSE, COHORT_UNVERIFIED, COVERAGE_UNVERIFIED, CONFLICTING_GAME, UNKNOWN_GAME_SEMANTICS, REQUEST_BUDGET_EXHAUSTED, NO_PROGRESS. No body/header/arbitrary exception text in errors.
- No response persistence/indexing or inbound server/MCP tool. NHL source permission does not alter independent Yahoo restrictions. Offline tests fail on accidental real networking.

## 7. Execution sequence after source decision and approval

One cohesive feature PR eventually, with five reviewable internal stages. Do not call a model-only or synthetic-only result a completed milestone. This task authorizes no PR or implementation.

### Stage 1: Data-source qualification (open prerequisite)

**Files:** This plan; docs/nhl-schedule.md during implementation.

- [ ] Establish applicable permission for limited automatic NHL retrieval; no paid/manual fallback.
- [x] Establish the publicly documented catalogue/window profile and historical explicit empty-day representation (section 2 follow-up). These are documented contracts, not current live validation.
- [ ] Establish source-date timezone/cutover mapping and bounded UTC envelope; validate current cohort, explicit empty buckets and window advancement in separately authorized acceptance after access is settled. Do not build a broad verifier framework.
- [ ] Record supported type/state mappings and unresolved exceptional states.
- [ ] If coverage cannot be established, report the exact blocker and propose one revised endpoint decision; never silently switch to 32 club calls or another provider.

Deliverable: evidence-backed source profile and minimal request sequence. No private file sample required. Essential access/coverage qualification is still open; the plan is not yet an executable approved live integration.

### Stage 2: Domain and pure intelligence

**Files:** domain/schedule.py, sports/nhl/schedule.py, tests/test_schedule_analysis.py, pyproject.toml, uv.lock (full source roots in section 3).

- [ ] Write synthetic failing tests for analyze_schedule: all-32 cohort/idle team, home-away, filters, complete/partial counts and deterministic ranking ties.
- [ ] Test UTC/local midnight, DST, unknown type/state, missing timestamps/context, same-day games and edge-crossing pairs. Incomplete counts suppress rankings; missing context alone affects B2B completeness.
- [ ] Implement the five contracts/pure rules and add/lock only approved tzdata.
- [ ] Run `uv run --locked --offline pytest tests/test_schedule_analysis.py`; all pass without network.

### Stage 3: Automatic NHL adapter

**Files:** providers/nhl/__init__.py, providers/nhl/schedule.py, tests/test_nhl_schedule.py.

- [ ] Write MockTransport tests for qualified catalogue/window shapes, exact paths, overlapping/missing/empty buckets, earliest missing bucket advancement, no progress, budgets/deadlines.
- [ ] Test catalogue/identity/season mismatch, conflicting duplicates, missing collections, explicit zero-day versus omitted bucket, per-day/root count mismatches, malformed fields, unknown optional semantics, duplicate keys, invalid encoding, oversized/compressed responses, redirects, rate limits and denial.
- [ ] Assert missing/invalid data never becomes complete zero counts; earlier valid windows survive as partial observations after later failure.
- [ ] Implement get_schedule from the qualified profile and section 6; no override may fabricate completeness.
- [ ] Run `uv run --locked --offline pytest tests/test_nhl_schedule.py tests/test_schedule_analysis.py`; all pass under network blockers.

### Stage 4: Human CLI

**Files:** src/fantasy_gm/schedule.py, tests/test_schedule_cli.py, README.md, docs/architecture.md, docs/nhl-schedule.md.

- [ ] Test no-I/O help/input errors, live intent, timezone errors, all-club output, escaped strings, partial alphabetical output without winner claims and documented exit codes.
- [ ] Assert no Yahoo provider/session/verifier imports, credential reads, source-data writes/logging or MCP enablement.
- [ ] Implement around get_schedule/analyze_schedule and document count/B2B/source/uncertainty semantics.
- [ ] Run `uv run --locked --offline pytest tests/test_schedule_cli.py`; all pass without live access.

### Stage 5: Validation, review and separately authorized live acceptance

- [ ] Run `uv run --locked --offline pytest`, `uv run --locked --offline ruff check .`, `uv run --locked --offline ruff format --check .`, `uv run --locked --offline mypy`, credential-pattern review and `git diff --check`. Preserve Yahoo regressions; never print secret matches.
- [ ] Complete independent review of coverage, time, identity, maintainability, privacy and transport; fix actionable findings and rerun affected checks.
- [ ] Separately authorize explicit endpoints/call budget for human-operated live acceptance without response persistence. Verify current cohort, all buckets for an explicit week, idle-team handling, representative home-away UTC/local times and all-team totals against the official schedule. Verify an empty/boundary period within that budget or record it unverified.
- [ ] Qualify exceptional-state examples only when reliably available; no manufactured live cancellation case. One observation cannot validate update history; record that limitation or use a later separately approved observation.
- [ ] Complete FGM-005 only after useful real all-club output succeeds. No publishing/merge authorization is implied.

## 8. Acceptance, remaining risks and review record

Accept useful all-current-club comparisons, explicit dates, opponents/home-away, local display, B2B indicators, known-state reporting and visible uncertainty with no Yahoo dependency. Partial output is a valid failure mode; permanently unavailable rankings from an unqualified source do not satisfy completion.

Remaining limitations: undocumented compatibility/quotas/support; no guaranteed real-world completeness/freshness; incomplete exceptional-state mappings and no change history; no historical cohort, player/roster join or fantasy optimization. Each invocation is a fresh observation, not continuous monitoring.

**Planning checks:** main/HEAD and repository boundaries inspected. The 544-test FGM-004 result is historical; not rerun for this documentation-only task. No live NHL/Yahoo requests, feature edits, installations, new branches or publication.

**Independent review completed 2026-10-16:** A separate read-only reviewer checked both the preceding architecture revision and the public-documentation follow-up. No actionable findings in either review. The follow-up review confirmed evidence labels, count-check limits, precise access/date-boundary gaps, aligned acquisition/acceptance stages and unchanged cost/privacy scope. No endpoint calls or edits by the reviewer. This does not establish source permission or live API compatibility.

**Next step:** Seek NHL clarification on the two precise questions in section 2: applicable automated-access permission and the source date/timezone/cutover contract. The published catalogue/window profile is established as documented evidence; do not repeat that investigation as though no schema were known. After the source gate is resolved, seek implementation approval; current behavior still requires separate bounded live acceptance. No paid service or manual sample is required by this design.
