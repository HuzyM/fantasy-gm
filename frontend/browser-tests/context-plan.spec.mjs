import { test, expect } from 'playwright/test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');

// Wholly fabricated protocol inputs; no private launcher, authentication or provider transport.
function observation(loaded) {
  return {
    mode: 'private',
    source: 'yahoo',
    provenance: ['FABRICATED CONTEXT REVIEW PROTOCOL'],
    planningWindow: { start: '2026-12-31', end: '2027-01-06', timezone: 'America/Toronto' },
    league: { name: 'Invented context league', season: 2026 },
    roster: {
      teamName: 'Invented roster',
      returnedCount: 3,
      contextUnverified: true,
      coverage: { kind: null, date: null, week: null },
      entries: ['first', 'second', 'third'].map((id, index) => ({
        id: `invented-context-${id}`,
        name: 'Invented Same Name',
        positions: ['D'],
        slot: 'IR',
        team: index === 2 ? null : 'TOR',
        affiliationUnverified: index === 2,
        scheduleStatus: index === 2 || !loaded ? 'AFFILIATION_UNVERIFIED' : 'MATCHED',
      })),
    },
    schedule: loaded
      ? {
          start: '2026-12-31',
          end: '2027-01-06',
          timezone: 'America/Toronto',
          observedAt: '2026-12-30T12:00:00Z',
          issues: ['FABRICATED_PARTIAL_COVERAGE'],
          teams: [
            {
              code: 'TOR',
              observedGames: 2,
              uncertainDated: 0,
              unplaced: 1,
              countComplete: false,
              backToBackComplete: false,
            },
          ],
          days: ['2026-12-31', '2027-01-01'].map((date, index) => ({
            date,
            count: { state: 'incomplete', value: 1, reason: 'Invented partial coverage' },
            games: [
              {
                id: `invented-context-game-${index}`,
                away: 'MTL',
                home: 'TOR',
                time: index ? '2027-01-02T00:30:00Z' : '2027-01-01T00:30:00Z',
                state: 'SCHEDULED',
                upcomingEligible: true,
              },
            ],
          })),
        }
      : null,
  };
}
async function protocol(page, loaded) {
  const requests = [],
    external = [],
    logs = [];
  let current = observation(loaded);
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/'))
      requests.push({ url: request.url(), body: request.postData() });
  });
  page.on('console', (message) => logs.push(message.text()));
  page.on('pageerror', (error) => logs.push(error.message));
  await page.route('**/*', (route) => {
    if (new URL(route.request().url()).origin === 'http://127.0.0.1:4173') return route.continue();
    external.push(route.request().url());
    return route.abort();
  });
  await page.route('**/axe-check.js', (route) =>
    route.fulfill({ contentType: 'application/javascript', body: axe }),
  );
  await page.route('**/api/status', (route) =>
    route.fulfill({
      json: { mode: 'private', yahoo: 'loaded', schedule: loaded ? 'observed' : 'unavailable' },
    }),
  );
  await page.route('**/api/view', (route) => route.fulfill({ json: current }));
  await page.goto('/#access=fabricated-context-capability-12345678901234567890');
  await expect(page.locator('.screen-content')).toHaveAttribute('data-source', 'private');
  return {
    requests,
    external,
    logs,
    replace() {
      current = { ...current, provenance: ['FABRICATED CONTEXT REPLACEMENT'] };
    },
  };
}
async function press(page, name) {
  await page.getByRole('button', { name, exact: true }).focus();
  await page.keyboard.press('Enter');
}
async function navigate(page, width, name) {
  if (width < 900) await press(page, 'Open navigation');
  await press(page, name);
  await expect(page.getByRole('main')).toBeFocused();
}
async function save(page, action, reason) {
  await page.getByLabel('Review action', { exact: true }).focus();
  await page.keyboard.type(action);
  await page.keyboard.press('Tab');
  await page.getByRole('textbox', { name: 'Reason', exact: true }).fill(reason);
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
}
async function check(page, width) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  await page.addScriptTag({ url: '/axe-check.js' });
  expect(
    await page.evaluate(
      async () =>
        (await window.axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa'] })).violations,
    ),
  ).toEqual([]);
}

for (const width of [1672, 1440, 768, 390])
  for (const loaded of [true, false]) {
    test(`context review keyboard journey ${loaded ? 'observed' : 'Yahoo-only'} ${width}`, async ({
      page,
      context,
    }, testInfo) => {
      await page.setViewportSize({ width, height: 941 });
      const evidence = await protocol(page, loaded);
      await expect(
        page.getByRole('button', { name: /Select Thursday, December 31:/ }),
      ).toBeVisible();
      await navigate(page, width, '03 My Roster');
      await press(page, 'Prepare roster review');
      await expect(page.getByRole('main')).toBeFocused();
      await expect(
        page.getByRole('combobox', { name: 'Returned player', exact: true }),
      ).toHaveValue('invented-context-first');
      await save(page, 'Invented roster verification', 'Invented manager reason for roster');
      const first = page.getByRole('article', { name: 'Review item 1' });
      await expect(first.getByText('invented-context-first', { exact: true })).toBeVisible();
      await press(page, 'Reopen context for item 1');
      await expect(page.getByRole('main')).toBeFocused();
      await expect(
        page.getByRole('heading', { name: 'My Roster', exact: true, level: 1 }),
      ).toBeVisible();
      await expect(
        page.getByText('Review context: 2026-12-31 · 2026-12-31 – 2027-01-06 · America/Toronto', {
          exact: true,
        }),
      ).toBeVisible();

      await navigate(page, width, '02 Schedule Planner');
      await press(
        page,
        loaded
          ? 'Select Friday, January 1: 1 observed games, total unknown; 2 roster team matches'
          : 'Select Friday, January 1: schedule unknown; roster coverage unknown',
      );
      await page
        .getByRole('combobox', { name: 'Planner review player', exact: true })
        .selectOption('invented-context-third');
      await press(page, 'Prepare Planner review');
      await expect(page.getByRole('main')).toBeFocused();
      await expect(page.getByLabel('Review date', { exact: true })).toHaveValue('2027-01-01');
      await save(
        page,
        'Invented unsupported affiliation check',
        'Invented verification; no game asserted',
      );
      await expect(
        page
          .getByRole('article', { name: 'Review item 2' })
          .getByText(/Schedule coverage unavailable/),
      ).toBeVisible();

      await navigate(page, width, '04 Compare Players');
      await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toHaveAttribute(
        'aria-selected',
        'true',
      );
      await expect(page.getByLabel('Statistics view', { exact: true })).toHaveCount(0);
      await page
        .getByRole('combobox', { name: 'Second player', exact: true })
        .selectOption('invented-context-third');
      await page
        .getByRole('combobox', { name: 'Second player', exact: true })
        .selectOption('invented-context-second');
      await page.getByLabel('Comparison review date', { exact: true }).fill('2026-12-31');
      await check(page, width);
      await page.screenshot({
        path: testInfo.outputPath(`context-comparison-${loaded}-${width}.png`),
        fullPage: true,
      });
      const reads = evidence.requests.length;
      await press(page, 'Prepare comparison review');
      await expect(page.getByRole('main')).toBeFocused();
      await expect(
        page.getByText(
          /Compared pair: Invented Same Name · invented-context-first \/ Invented Same Name · invented-context-second/,
        ),
      ).toBeVisible();
      await save(page, 'Invented pair assignment check', 'Invented manager reason for pair');
      const pair = page.getByRole('article', { name: 'Review item 3' });
      await expect(pair.getByText('invented-context-first', { exact: true })).toBeVisible();
      await expect(pair.getByText('invented-context-second', { exact: true })).toBeVisible();
      if (loaded) {
        await expect(
          pair.getByText(
            'Shared game date observed; review prompt only, not a slot-capacity conflict.',
            { exact: true },
          ),
        ).toBeVisible();
        await expect(pair.getByText(/Back-to-back opportunity observed/)).toHaveCount(2);
        await expect(pair.getByText(/1 unplaced observations/)).toHaveCount(2);
      }
      await press(page, 'Edit item 3');
      await expect(page.getByLabel('Review action', { exact: true })).toBeFocused();
      await page.getByLabel('Review action', { exact: true }).fill('Invented edited pair action');
      await press(page, 'Save review item');
      await press(page, 'Mark item 3 reviewed');
      await expect(pair.getByText('Reviewed', { exact: true })).toBeVisible();
      await check(page, width);
      await page.screenshot({
        path: testInfo.outputPath(`context-plan-${loaded}-${width}.png`),
        fullPage: true,
      });
      await press(page, 'Reopen context for item 3');
      await expect(page.getByRole('main')).toBeFocused();
      await expect(page.getByRole('combobox', { name: 'First player', exact: true })).toHaveValue(
        'invented-context-first',
      );
      await expect(page.getByRole('combobox', { name: 'Second player', exact: true })).toHaveValue(
        'invented-context-second',
      );
      await expect(page.getByLabel('Comparison review date', { exact: true })).toHaveValue(
        '2026-12-31',
      );
      await press(page, 'Swap players');
      await page.getByLabel('Find a comparison player', { exact: true }).fill('hide choices');
      await press(page, 'Next comparison week');
      await expect(
        page.getByRole('button', { name: 'Prepare comparison review', exact: true }),
      ).toBeDisabled();
      await expect(
        page.getByText(/Context review unavailable for an unloaded alternate window/),
      ).toBeVisible();
      await page.goBack();
      await expect(page.getByRole('region', { name: 'Manual plan', exact: true })).toBeVisible();
      await expect(pair.getByText('2026-12-31', { exact: true })).toBeVisible();
      await press(page, 'Return item 3 to pending');
      await press(page, 'Reopen context for item 3');
      await expect(page.getByRole('main')).toBeFocused();
      await expect(page.getByRole('combobox', { name: 'First player', exact: true })).toHaveValue(
        'invented-context-first',
      );
      await expect(page.getByRole('combobox', { name: 'Second player', exact: true })).toHaveValue(
        'invented-context-second',
      );
      expect(evidence.requests).toHaveLength(reads);
      expect(page.url()).toMatch(/#comparison$/);
      expect(await page.evaluate(() => JSON.stringify(history.state))).not.toMatch(
        /invented-context|2026-12|2027-01/,
      );
      expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([
        0, 0,
      ]);
      expect(await context.cookies()).toEqual([]);
      expect(evidence.external).toEqual([]);
      expect(evidence.logs).toEqual([]);
      expect(JSON.stringify(evidence.requests)).not.toMatch(
        /invented-context|Invented.*reason|2026-12|2027-01/,
      );
    });
  }

test('replacing a fabricated source discards pair items and opaque return context', async ({
  page,
}) => {
  const evidence = await protocol(page, true);
  await navigate(page, 1672, '04 Compare Players');
  await press(page, 'Prepare comparison review');
  await expect(page.getByRole('main')).toBeFocused();
  await save(page, 'Invented discarded pair', 'Invented discarded reason');
  await press(page, 'Record no action needed');
  evidence.replace();
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.getByText('Invented discarded pair', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Manual plan', exact: true })).toBeVisible();
  await press(page, 'Manual plan');
  await expect(page.getByRole('article')).toHaveCount(0);
  await expect(page.getByText('Review pending.', { exact: true })).toBeVisible();
  await page.goBack();
  await expect(page.getByText('Invented discarded pair', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Invented discarded reason', { exact: true })).toHaveCount(0);
});
