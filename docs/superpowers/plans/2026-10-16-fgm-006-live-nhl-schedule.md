# FGM-006 PuckAPI Schedule Integration Implementation Plan

**Decision, 2026-10-16:** The operator selected PuckAPI and authorized implementation on feature/fgm-006-puckapi-schedule from main 635fc348339bbd7edcecd42341a2696300201b23. This supersedes the earlier NHL-operated source proposal. No real provider calls, credential inspection, commits, pushes or PRs are authorized during development.

**Goal:** Retrieve real NHL schedule observations through documented PuckAPI REST, retaining the FGM-005 models, analysis and standalone CLI.

**Architecture:** providers/puckapi.py -> immutable domain.schedule -> pure sports.nhl.schedule -> fantasy_gm.schedule. No Yahoo dependency, new package dependency, persistence, provider framework or background refresh. The NHL-operated adapter stays synthetic-only.

## Source and contracts

- [PuckAPI terms](https://puckapi.com/terms) permit personal API projects. This is the selected documented access route, not a claim of NHL affiliation or independent underlying-rights clearance.
- [REST conventions](https://puckapi.com/docs): authenticated POST with x-api-key, results inside data, fixed HTTP errors including authentication, credits and rate limits. No games cursor/offset is documented.
- [get_games](https://puckapi.com/docs/get-games): explicit date_from/date_to/season, optional regular/preseason/playoff filter, limit 1-500. [list_teams](https://puckapi.com/docs/list-teams) supplies codes and names. The [published club directory](https://puckapi.com/teams) supports the current 32-code cohort.
- The operator reports successful finished-CLI acceptance for October 17–23 (47 games) and October 29–November 4 (48 games), 2026, with 32-team cohort, observed-count reconciliation and DST/B2B checks passing. Both runs retained COVERAGE_UNVERIFIED and exit 1. These sampled observations do not establish complete coverage. No supplied real game records enter fixtures.
- Docs show time-only startTime; the operator observed ISO UTC timestamps. Only full ISO timestamps with explicit offsets become UTC instants. Missing, naive or time-only values stay unplaced. Do not combine gameDate with an assumed timezone.

## Tasks

1. Synthetic tests first, then one bounded PuckApiScheduleClient and allowlisted PuckApiError in src/fantasy_gm/providers/puckapi.py. Read PUCKAPI_API_KEY only at runtime. Use exact MockTransport injection in automated tests.
2. Validate bounded unique team codes and opaque game IDs, selected season/type, catalogue membership, timestamps and duplicate/conflicting games. Team code is the documented identity; do not invent numeric IDs. Qualify the exact 32-code set for 20262027, not any 32 rows. Other seasons do not inherit that qualification.
3. Fetch teams once and games once. Default result limit 500, optional lower CLI cap. Normally six credits total; no automatic splitting, retry, top-up or paid fallback. Detect limit saturation and inconsistent declared counts.
4. Request a candidate reported-date envelope start-3 through end+3: adjacent-day B2B context plus two guard dates on each side. This is not proof of date coverage. Until date-cutover and completeness evidence is established, keep coverage_contract_verified false, covered_dates empty and COVERAGE_UNVERIFIED explicit. Observed counts and B2B pairs remain useful; zeros, complete B2B claims and global rankings stay unqualified.
5. Add explicit --puckapi alongside --demo; preserve --live as the disabled NHL-operated mode. Support regular/preseason/playoff/all. Live wording identifies PuckAPI, partial information, observation time and source-date/UTC provenance. Show undated games without guessing local dates. Preserve B2B grouping and tied-ranking cleanup.
6. Update provider tests, CLI tests, test environment isolation and schedule/README/architecture documentation. Keep existing models, calculations, Yahoo behavior and dependencies unchanged.
7. Full locked offline pytest, Ruff lint/format, strict mypy, credential and whitespace checks. Independent whole-diff review and actionable corrections. No commit/push/PR.

## Safeguards

Only fixed https://mcp.puckapi.com/v1/list_teams and /v1/get_games. Read-only retrieval uses documented POST. TLS verification, no redirects/proxies/retries or cookies, bounded timeouts, 2 MiB raw response limit, best-effort 90-second deadline, at most two calls and six-second spacing for low-balance rate limits. No HTTP detail logging or arbitrary provider exception/error text. Reject reflected credentials before normalization.

Use dummy keys and fabricated responses in every test. No live PuckAPI/NHL/Yahoo calls from Codex, no actual credential reads or response recording. Yahoo-backed AI/MCP stays disabled, with no changes to OAuth/settings/rosters or privacy policies.

## Acceptance and limits

The operator completed the two private live CLI checks described above using a shell-session-only key. The schedule guide retains exact commands for future intentional use and explains exit codes and estimated credits. No further live session is required merely to remove COVERAGE_UNVERIFIED.

Remaining questions: date filter inclusivity/cutover, historical cohort coverage, full league completeness, optional metadata and exceptional status codes. Unsupported statuses stay unknown. No schedule-change history or source freshness guarantee. A later evidence-backed qualification can enable source-relative completeness; do not add an assume-complete switch or a verification framework.

Human-reported acceptance is complete for the displayed observations in those windows. Formal schedule completeness remains unverified: a valid empty response is not a proven zero, and a below-limit result is not completeness evidence. The final focused review corrected malformed offset-minute acceptance while preserving the same models, coverage flags and analysis. Development uses only synthetic transport tests. Progress and review results are recorded in the ignored .tools/fgm006-progress.md ledger until the user authorizes publication.
