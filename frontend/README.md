# Fantasy GM Dark Arena frontend

This milestone implements **Overview only**, using local synthetic fixtures. It does not connect to Python, Yahoo, PuckAPI or MCP. It has no accounts, persistence, analytics, paid services or provider credentials. The other sidebar entries explain that their screens are planned; they do not navigate to placeholder implementations.

## Run

Use Node.js 22.x (22.13+), 24.x, or 26+. This matches the shared runtime support of the locked dependencies, including Vitest and jsdom; Node 20, 23 and 25 are unsupported. Node 22.15.0 and npm 11.3.0 were used for validation.

```sh
cd frontend
npm ci --ignore-scripts
npm run dev
```

Open the loopback URL printed by Vite. The production output is static files in `dist/`, with no Node server requirement for the eventual Python integration. All fonts and artwork are local assets.

## Check

```sh
npm test
npm run typecheck
npm run format:check
npm run build
npm run test:browser
```

The browser check builds the application, starts a temporary loopback preview on port 4173, launches installed Google Chrome headlessly, and closes both on exit. Close another process on that port before running. To use an installed Playwright Chromium instead, install it with `npx playwright install chromium` and set `PLAYWRIGHT_CHANNEL=chromium`. No fantasy API access is involved.

Browser checks exercise filtering, inspection, expansion, week navigation, unsupported features and the mobile menu; fail on page overflow, external requests and console errors; and run axe WCAG A/AA checks on the initial desktop and phone states. Automated checks do not certify every accessibility state. Screenshots and JSON results are written to ignored `output/playwright/`. Screenshots contain synthetic sports data, attributed licensed photographs and official team logos; logo redistribution/commercial permission remains unconfirmed (see ASSETS.md).

## Structure and contracts

- `src/screens/Overview.tsx`: Overview state and composition. `App.tsx` mounts this screen only.
- `src/components/`: shared shell, panel/button/data-value primitives, keyboard-accessible tabs, day cards, roster table and player inspection.
- `src/view-model.ts`: immutable presentation contracts and small pure selection/date functions.
- `src/fixtures/overview.ts`: illustrative 2026–27 fixture week, players and schedules. This directory is intentionally separate from the repository's ignored provider `data/` directories.
- `src/styles.css`: reference-derived midnight-blue tokens, controlled glow, desktop composition and responsive rules.
- `scripts/verify-browser.mjs`: repeatable browser checks, screenshot capture and request isolation.

`Datum<T>` is a discriminated union: `verified` has a supplied value; `incomplete` preserves an observed value plus a reason; `unknown` and `unsupported` have a reason and **no value**. Provenance is a separate contract. “Verified” inside a synthetic fixture means that its authored value is supplied, not that it is real or current sports information. Zero stays zero, an observed zero never becomes a complete total, and missing values never become zero. Numeric rendering is centralized in `DataValue`.

Only the populated fixture week is available. Next/previous week deliberately show unknown coverage and unknown next team games. “Demo week” returns to the populated fixture, rather than pretending the illustrative week is today. Thursday demonstrates partial coverage; the game-log tab explains unsupported data; the Injured filter shows reported designations only; unknown injury status never means healthy. Roster/player actions stay within Overview.

## Injury and identity boundaries

`injury: Datum<InjuryDesignation>` is independent of `rosterSlot: Datum<string>`. DTD, Out, IR and IR+ are reported injury designations; an IR/IR+ slot alone never adds someone to Injured. Injured players remain in positional groups, and counts use the full roster independently of search. Unknown/unsupported reports are excluded from reported counts, not treated as healthy.

The six real NHL identities have unknown injury data. Three explicitly fictional demo entries provide DTD, IR+ and Healthy examples without attributing invented medical information to a real person. There are nine rows, with six visible initially and the rest available by scrolling. Empty injury results explain missing reports versus search results.

`src/media.ts` centralizes photo and team identity/source metadata. `PlayerHeadshot` selects by NHL ID and rejects conflicting canonical names. `LocalImage` handles loading, failure and missing assets for photographs and logos. Files are local; no runtime image service or provider integration is added. Image credits expose the photographers, sources, licenses and visual adaptations. See [ASSETS.md](ASSETS.md) for research and licensing limitations.

## Visual source and deliberate differences

The user's approved `screens/01_Overview.png` from `Fantasy_GM_Approved_Dark_Arena_Designs.zip` controls the composition. No screen, card, table or chart is implemented as a screenshot background. The decorative arena is separate from semantic DOM controls. A single PlayerHeadshot component uses authentic, ID-verified historical photographs in roster and inspection views.

The implementation retains the 260px reference sidebar at 1672px width, 78px header, seven day cards, roster/inspection split and panel start at y=418. Smaller layouts collapse navigation and contain horizontal scrolling inside the schedule/table. The inspector stacks below the table rather than squeezing it.

Intentional differences: coherent 2026 fixture dates; a clearly labeled synthetic source; All Players initially selected to match the mixed-position reference rows; accurate fixture group counts; partial/unknown states; an unavailable game log; and a Demo Week reset. Historical Creative Commons photographs replace every generated player portrait, and official NHL dark-background logos replace generic marks. The photo, pose, uniform and original arena differ from the approved screenshot; no pixel-exact imagery claim is made. Official logo redistribution/commercial permission has not been established. See [asset provenance](ASSETS.md) and the [milestone review](../docs/frontend-overview.md).

Future integration must translate domain observations at a narrow boundary and preserve certainty, source, season and time context. Do not import Python/provider transports into this UI, add browser token storage, or wire future screens before review of this milestone.
