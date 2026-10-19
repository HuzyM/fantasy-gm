# Dark Arena local preview acceptance

The implementation is delivered through dependent reviewable PRs, without merging:
PR #9 roster/profile; #10 planner/comparison; #11 league/connections/settings;
the final local API/release PR is based on #11. Each branch preserves the preceding
milestones. The final branch contains the complete runnable application.

## Implemented data support

| Screen | Local functionality | Provider limitations |
| --- | --- | --- |
| Overview | Week/day selection, expandable games, search/filter/sort, inspection and profile navigation | Reported Yahoo roster and optional PuckAPI observations; no confirmed appearances, performance or injury feed |
| My Roster | Dynamic positional/injury filters, dense statistics, separate bench/reserve slots | Returned rows are not completeness or legality proof; Yahoo injuries and NHL identity crosswalk unavailable |
| Player Profile | Exact selected identity, shared portrait/fallback, stats tabs, schedule and comparison navigation | Licensed photos use verified curated NHL IDs only; unmapped Yahoo identities receive fallbacks; no live performance/history/news/advice |
| Schedule Planner | Daily away/home matchups, selected-game detail, dates/weeks, roster coverage | Pure Python analysis reused; unverified affiliation joins excluded; coverage, unplaced games and incomplete B2Bs remain explicit |
| Player Comparison | Two independent selectors, swap, combined search, totals/per-game views and schedules | Provider statistics unavailable; no invented projections or history; two supplied players required |
| League | Riverside synthetic standings, sort/search and matchup weeks | Other preview leagues have no competition data. Private mode shows reported league/team only; scores/standings/playoffs/settings/activity not fetched by this bounded session |
| Connections | Coarse source state, observation limits, local disconnect | Loaded observation is not ongoing health; provider refresh requires a new human launcher load |
| Settings | Session-wide logos/spacing/contrast, expandable sample previews and credits | Other selectors affect the labeled preview; no persistence, push alerts, unsupported theme or projection service |

## Local verification

- 802 Python tests, including 19 new API/date/security cases; Ruff and strict mypy pass.
- 59 frontend tests, including transport tests with wholly synthetic private-protocol inputs.
- Frontend formatting, types and production build pass. Production JavaScript is approximately 100 kB gzip; no new frontend runtime dependency was added.
- A clean Git source export with a fresh locked dependency install reproduces formatting, types, all 59 frontend tests and the production build. The lockfile verifies offline. Linux CI runs Python regressions with the 26 existing Windows-only input tests skipped, and checks types against the Windows target used by the guarded terminal APIs.
- All eight screens pass 32 production browser cases against the default synthetic Python server at 1672×941, 1440×900, 768×1024 and 390×844. Tests check overflow, loaded local assets, keyboard/control interactions, no external browser requests, no page errors and automated axe WCAG A/AA rules.
- Three additional browser cases (desktop/mobile transport and restart rotation) exercise private bootstrap, authorization headers, exact identity/fallbacks, private-ID-free URLs, absence of browser storage/cookies and disconnect using synthetic protocol inputs only.
- The retained Overview browser interaction regression remains part of CI. Same-platform screenshot assertions use reviewed Windows baselines under `docs/frontend/win32`; Linux CI captures evidence independently of Windows font rasterization.
- Backend boundary review completed independently with no actionable findings. Final integration review identified a P1 stale-session gap on server restart. Private checks now authenticate the capability against the local in-memory view on every poll/focus; unit and browser regressions reject old capabilities and clear the display. GitHub review additionally identified public transient-error recovery, observed-date month formatting and launcher interpreter instructions; all have focused regressions or corrected commands. Independent verification is required before handoff. Automated checks do not certify assistive technology or live provider correctness.

## Intentional visual differences

All eight approved screenshots control composition, palette and panel hierarchy.
Historical licensed action photographs cannot reproduce generated poses, signatures
or uniforms. Fixture player counts derive from loaded rows. Unsupported facts are
shown as unavailable; fictional account health, forecasts, current injuries, scores
and confirmed appearances are never substituted. Tables scroll locally and panels
stack on small screens. Settings has a collapsed preview so unsupported global
behavior is not implied. Official NHL logo usage/redistribution rights remain
unresolved in `frontend/ASSETS.md`; no commercial clearance is claimed.

## Human-only acceptance still required

Default synthetic local use is verified. The new private browser integration and
live public schedule observation have **not** been exercised by an agent. To accept
them, close AI/MCP, browser automation, recording, remote views and screen sharing;
then follow `docs/local-application.md` in a private human terminal.

Confirm selected league/team/roster display against your own Yahoo page, retained
unknown injury/performance/coverage labels, missing NHL-photo mappings, no writes,
disconnect/expiry and no saved state after restart. Public schedule loading requires
its separate confirmation and at most two existing PuckAPI requests, normally six
credits; compare observed games against the chosen published window and preserve
coverage caveats. Do not send account fields, tokens, URLs containing access keys,
response bodies or private screenshots back to an AI tool. This acceptance cannot
be replaced by synthetic tests.

No additional provider, paid service or remote deployment is enabled. Richer player
statistics, injuries, league competition data and identity crosswalks require
separate verified contracts. No PR will be merged without owner approval.
