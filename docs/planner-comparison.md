# Schedule Planner and Player Comparison

Dependent milestone: base branch `feature/dark-arena-roster-profile` (PR #9). No merges are performed.

Planner preserves the approved seven-day calendar above a daily away/home matchup table and selected-game panel. Date, week, roster-only and highlight controls work on the loaded synthetic sample. Exact team codes determine roster membership; no appearance is confirmed. The partial Thursday fixture retains unknown totals. Other weeks have unknown coverage, not zero games. Counts and uncertainty are announced with each date.

Comparison preserves large cinematic portraits on either side of a generous central gap. Both player selectors, swap, search, totals/per-game modes and keyboard tabs work. Per-game statistics require a complete positive games-played denominator. Unknown or unsupported data remains explicit. Existing verified photographs are reused; the sample compares Matthews and MacKinnon because no verified McDavid asset/identity is loaded. Rankings, projections, head-to-head history, news and game logs are unavailable.

Validation: eight focused behavior tests; existing tests retained (40 frontend tests in this branch). Production browser checks and axe rules pass at 1672, 1440, 768 and 390 pixels, with no horizontal page overflow, external browser requests or console errors. The browser tests exercise daily matchup selection, unknown weeks, player swapping and keyboard tabs at every width. Production screenshots and reviewed Windows baselines are in `docs/frontend/win32`; comparison is repeatable with `VISUAL_COMPARE=1 npx playwright test` on Windows.

Reference differences are deliberate: clearly labeled synthetic dates/statistics, existing identity-safe historical portraits, no generated studio pose, no invented advice, probability, records or unsupported history chart. Smaller screens contain wide tables and stack panels. Asset rights limitations are unchanged; see `frontend/ASSETS.md`. No Python/provider changes are included.
