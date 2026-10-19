# League, Connections and Settings

Dependent milestone: base `feature/dark-arena-planner-comparison` (PR #10). No merges are performed.

League follows the approved standings/current-matchup/weekly-matchups composition, with settings, activity and playoff panels beneath. The supported Riverside sample includes standings sorting, search, expansion and week navigation with clearly labeled synthetic examples. Other preview leagues do not have competition data. Unloaded weeks never inherit example scores. There is no provider-backed scoreboard, probability, activity or qualification claim.

Connections retains the approved account, metrics, league selector, activity, permissions and tools layout, but accurately shows disconnected and unverified state. No account identity, last-sync timestamp, health or token expiry is fabricated. Authentication is not part of this frontend-only milestone.

Settings preserves the approved category navigation and general/display/notification/scoring/account panels. Logos, compact spacing and high contrast apply across the app in memory for the current session. Other supported selectors change an explicitly synthetic expandable preview. Notifications, projections, roster percentages and unsupported themes are disabled with explanations. No preferences enter localStorage, cookies or network requests.

Validation: 46 frontend tests in this branch, including five focused screen tests and session-wide preference navigation. Twelve browser cases cover all three screens at desktop 1672×941, laptop 1440×900, tablet 768×1024 and mobile 390×844, with axe WCAG A/AA rules, no page overflow, no external requests or browser errors. Browser interactions cover sorting/unloaded scores, disconnected guidance and disabled sync, preference changes and hash-safe category navigation. Screenshots and same-platform comparisons are in `docs/frontend/win32`.

Reference differences: synthetic competition data is prominently labeled; fictional Yahoo identity, healthy sync, timestamps, probabilistic advice and transactions are replaced with truthful unavailable states. Settings includes an expandable preview to demonstrate controls without inventing live behavior. Desktop density was tightened after visual comparison. Mobile panels stack and wide tables scroll locally. Historical photo and official-logo attribution/rights limitations remain in `frontend/ASSETS.md`.
