# My Roster and Player Profile

Milestone 1 starts from merged Overview `c0cf4b2`. Shared shell navigation uses a small allowlisted hash route; the roster table, injury filter, inspection panel, image identity resolver and local logo assets are reused. Profile navigation preserves the exact selected identity. Unknown identities have an explicit unavailable view and no substitute portrait.

My Roster adds a dense statistics view, summary counts derived from loaded players, and separate bench/reserve sections derived from reported slots. An injury filter is independently derived from supplied designations. Reserve occupancy proves neither injury nor lineup legality.

Player Profile follows the reference's large portrait, summary statistics, performance chart, season table, outlook, schedule, considerations and quick-action panels. Fixture series are explicitly synthetic. Projections, ownership, advice, rank, advanced statistics, splits, game logs and news remain unavailable. Team games never imply an appearance. Writes stay disabled.

## Verification

Component regression coverage includes roster/profile navigation, exact identity, unknown identity fallbacks and distinct slot/injury subsets. Existing Overview tests are retained. Browser checks cover desktop 1672×941, laptop 1440×900, tablet 768×1024, mobile 390×844, keyboard tabs, fixture selection, no page overflow, decoded local assets, no external requests, no browser errors and automated axe WCAG A/AA rules. These automated checks are not assistive-technology certification.

Production screenshots and same-platform visual baselines are in `docs/frontend/win32`. Run `VISUAL_COMPARE=1 npx playwright test` with an environment variable appropriate to the shell to compare; add `--update-snapshots` only after inspecting intentional visual changes. CI captures screenshots on Linux without asserting against Windows font rasterization. The test's platform-specific baseline path also supports separately reviewed Linux baselines. CI uploads browser evidence and runs formatting, types, tests, build and both browser checks.

## Differences from the approved references

- Nine loaded fixture players rather than the reference's illustrative 18-player squad; counts derive from actual loaded data.
- Historical licensed action photographs replace generated studio portraits. They cannot reproduce a fabricated pose, jersey or signature. No new artwork rights are claimed.
- Current fixture period is explicitly a demo, with unknown real injuries and fictional injury examples.
- Unsupported projections, line combinations, play probabilities, league ranks, news and transactions are explained rather than represented as working data.
- On smaller screens the tables scroll in their own containers and panels stack. The reference supplies desktop compositions only.

Asset attribution and unresolved official-logo usage rights remain recorded in `frontend/ASSETS.md`. No Python/provider or Yahoo privacy changes are included in this milestone.
