# Fantasy GM Dark Arena frontend

All eight approved screens are implemented as reusable React components: Overview, Schedule Planner, My Roster, Player Profile, Player Comparison, League, Connections and Settings. Player Profile opens contextually from a selected player. Navigation uses a small allowlisted hash route; no routing/state framework or paid service is needed.

## Run locally

Use Node **22.13+ within 22.x, 24.x, or 26+** (`^22.13.0 || ^24.0.0 || >=26.0.0`) and Python 3.12+. Node 20, 21, 23 and 25 are outside the supported dependency range. CI pins Node 22.15.0.

From the repository root, run `uv sync --locked`, then in this directory run `npm ci` and `npm run build`. Return to the root and run `.venv/Scripts/python.exe -B -m fantasy_gm.web`, or use `scripts/start-local.ps1`. Open http://127.0.0.1:8765/ using the exact numeric host. The default run is synthetic, reads no provider credentials and makes no provider requests. `npm run dev` remains available for frontend-only development.

The optional private browser session is **human-operated only**: close AI/MCP, browser automation and recording first. See [local application instructions](../docs/local-application.md) before using it. Never paste credentials, tokens or private fantasy information into this chat, tests, screenshots or saved files.

## Verification

- `npm run format:check`
- `npm run typecheck`
- `npm test`
- `npm run build`
- `npm run test:browser` for the retained Overview interaction regression
- `npx playwright test` for all eight screens at desktop, laptop, tablet and mobile, with axe rules and local assets
- Set `LOCAL_API=1` to run those checks against the default synthetic Python server. Set `PYTHON_EXECUTABLE` if your interpreter is elsewhere.
- Set `VISUAL_COMPARE=1` to compare reviewed same-platform screenshots in `docs/frontend/<platform>`. Add `--update-snapshots` only after reviewing intentional changes. CI captures Linux evidence; Windows baselines are not used to assert Linux font rasterization.

No automated check authorizes live providers or private browser sessions. Synthetic protocol tests verify private transport without reading a real account. Accessibility automation supplements keyboard checks; it is not assistive-technology certification.

## Data boundaries and limitations

Certainty (`verified`, `incomplete`, `unknown`, `unsupported`) is separate from provenance. Every demo screen labels its synthetic values. Missing injury reports never mean healthy; roster slots do not establish injury status. Team games never prove appearances. Incomplete and absent coverage never become complete game counts or guaranteed off-days.

The local API reuses the Python schedule analysis and Yahoo owned-team reader. Browser GETs read process memory; only the human launcher loads providers. Private tokens never enter browser responses. The browser keeps an opaque capability in memory, removes its bootstrap fragment, uses an authorization header, and clears the private display on disconnect, observed expiry or server failure. No private-to-demo fallback occurs. No private Yahoo IDs enter route URLs.

Yahoo supplies reported roster identity/positions/affiliations only in this browser load. NHL photo identity cannot be inferred from a matching name: unmapped Yahoo identities receive graceful image fallbacks. Real injuries, performance statistics, game logs, forecasts, ownership, line combinations, league scores/standings and live news need additional verified provider contracts. Such values remain unavailable. There are no roster transactions, lineup writes, trades or automated refreshes.

Display preferences stay in memory. Logos, compact spacing and contrast affect the app; date-range/stat-format/chart/time controls affect an expandable labeled sample preview. Unsupported notifications/themes/projections remain disabled. Closing the app resets preferences.

## Visual references and assets

The eight approved Dark Arena screenshots control the navy/cyan composition, large player portraits, daily matchup table and generous comparison separation. No screenshot is used as a screen background. The arena is decorative; controls, tables and charts are semantic DOM. Responsive layouts contain wide tables and stack panels.

`src/media.ts`, `PlayerHeadshot`, `LocalImage` and `TeamMark` preserve the original verified photo/logo registry and loading/missing/error fallbacks. Real, historical licensed photographs replace generated player portraits. IDs and canonical names must agree before a curated photograph is shown. Six real identities and three fictional injury examples demonstrate the synthetic roster.

[ASSETS.md](ASSETS.md) records creators, exact source pages, licenses and photo treatments. Official NHL logo redistribution/commercial permission remains unresolved. Historical action poses, uniforms and the decorative arena differ from the reference. Unsupported facts are explained rather than drawn as real measurements. Per-milestone comparison notes and production screenshots are in `docs/`.
