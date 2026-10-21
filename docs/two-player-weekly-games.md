# Two-player weekly game comparison

Open **Compare Players** to compare two distinct players from the loaded roster;
observed mode opens **Schedule** by default. The seven inclusive Toronto calendar
dates start at the explicit launcher planning window, including Yahoo-only mode
without a schedule, or December 7 in the explicitly synthetic demo. Planner's
**Compare players** action opens Schedule with its exact selected window. Previous
and next week move seven calendar dates while retaining the pair. Swaps and player
changes retain the selected window, including through Statistics and History.
The human chooses that window before separate public-load consent; see
[local operation](local-application.md). Yahoo-only opportunities are unavailable;
zero or one returned player cannot supply a comparison pair. Neither degraded mode
certifies the full release journey.

Each date shows both reported teams' observed games, opponent, home/away, available
Toronto start time and status. On mobile, both players stack beneath each date.
The summaries show observed scheduled games, back-to-back opportunities and shared
game dates. Same-team players have matching schedules; a game between the two
reported teams contributes one shared date. Multiple games on one date do not
multiply date-based opportunities, and a same-day anomaly is labelled.

Scheduled counts require affirmative source eligibility, a scheduled state and a
valid recorded UTC start. Elapsed start times do not remove scheduled observations.
Identical repeats collapse; contradictory game IDs are disputed and excluded from
all opportunity counts, even when a conflicting variant lies outside the week.
Attributable excluded observations remain visible with status and reason. No
variant is selected as authoritative and unavailable times stay unverified.

Reported affiliations may be stale and do not establish NHL identity or player
appearances. An unavailable affiliation join produces unknown summaries. Partial
coverage retains known games with incomplete-total qualifications. Empty dates say
“No qualifying game observed”; they do not establish an off-day. Unloaded dates
have unknown coverage and never trigger a provider request or substitute demo data.
Zero observed opportunities does not prove none exist in a complete schedule.
Source observation time and synthetic provenance remain visible.

Carried navigation context lives only in the mounted application. History uses
opaque keys; identities, display data and the weekly window are not placed in
history payloads. Locking, disconnecting or replacing source observations clears
the context, and history navigation cannot restore it. This feature introduces
no storage, cookies, provider refresh, endpoint or dependency.

Verification covers rendered comparison behavior in
`frontend/tests/comparison-games.test.tsx`, Planner navigation in
`frontend/tests/application.test.tsx`, existing roster-week/calendar regressions,
and synthetic browser checks in `frontend/browser-tests/comparison-games.spec.mjs`.
The browser checks capture Schedule at desktop, laptop, tablet and mobile sizes,
check actual column/stack layout, keyboard tabs, accessibility, privacy, replacement
and lock/history behavior. Existing screenshot comparison gates remain in force;
new captures do not automatically replace their baselines.
