import { test, expect } from 'playwright/test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');

// Fabricated protocol only; never authenticate or launch a real private session.
function observation(loaded) {
  return {
    mode: 'private',
    source: 'yahoo',
    provenance: ['FABRICATED MANUAL PLAN PROTOCOL'],
    league: { name: 'Invented manual plan league', season: 2026 },
    planningWindow: { start: '2026-12-31', end: '2027-01-06', timezone: 'America/Toronto' },
    roster: {
      teamName: 'Invented team',
      returnedCount: 2,
      contextUnverified: true,
      coverage: { kind: null, date: null, week: null },
      entries: [0, 1].map((index) => ({
        id: `fabricated-plan-${index}`,
        name: 'Invented Same Name',
        positions: ['D'],
        slot: 'IR',
        team: index ? null : 'TOR',
        affiliationUnverified: !!index,
        scheduleStatus: loaded && !index ? 'MATCHED' : 'AFFILIATION_UNVERIFIED',
      })),
    },
    schedule: loaded
      ? {
          start: '2026-12-31',
          end: '2027-01-06',
          timezone: 'America/Toronto',
          observedAt: '2026-12-30T12:00:00Z',
          issues: ['COVERAGE_UNVERIFIED'],
          teams: [],
          days: [
            {
              date: '2026-12-31',
              count: { state: 'incomplete', value: 1, reason: 'Fabricated partial coverage' },
              games: [
                {
                  id: 'invented-game',
                  away: 'MTL',
                  home: 'TOR',
                  time: '2027-01-01T00:30:00Z',
                  state: 'SCHEDULED',
                  upcomingEligible: true,
                },
              ],
            },
          ],
        }
      : null,
  };
}
async function protocol(page, loaded) {
  const external = [],
    requests = [],
    logs = [];
  let current = observation(loaded),
    available = true;
  page.on('pageerror', (error) => logs.push(error.message));
  page.on('console', (message) => logs.push(message.text()));
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/'))
      requests.push({ url: request.url(), body: request.postData() });
  });
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
      json: {
        mode: 'private',
        yahoo: available ? 'loaded' : 'expired',
        schedule: loaded ? 'observed' : 'unavailable',
      },
    }),
  );
  await page.route('**/api/view', (route) => route.fulfill({ json: current }));
  await page.route('**/api/disconnect', (route) => route.fulfill({ json: { disconnected: true } }));
  await page.goto('/#access=fabricated-plan-capability-12345678901234567890');
  await expect(page.locator('.screen-content')).toHaveAttribute('data-source', 'private');
  return {
    external,
    requests,
    logs,
    replace() {
      current = { ...current, provenance: ['FABRICATED REPLACEMENT'] };
    },
    expire() {
      available = false;
    },
    reopen() {
      available = true;
    },
  };
}
async function keyboardButton(page, name) {
  const button = page.getByRole('button', { name, exact: true });
  await button.focus();
  await page.keyboard.press('Enter');
}
async function navigate(page, width, name) {
  if (width < 900) await keyboardButton(page, 'Open navigation');
  await keyboardButton(page, name);
}
async function openPlan(page, width) {
  await navigate(page, width, '02 Schedule Planner');
  await keyboardButton(page, 'Manual plan');
  return page.getByRole('region', { name: 'Manual plan', exact: true });
}
async function createItem(page) {
  await page.getByRole('combobox', { name: 'Returned player', exact: true }).focus();
  await page.keyboard.press('End');
  await expect(page.getByRole('combobox', { name: 'Returned player', exact: true })).toHaveValue(
    'fabricated-plan-1',
  );
  await page.keyboard.press('Tab');
  await page.getByLabel('Review date', { exact: true }).fill('2027-01-06');
  await page.getByLabel('Review action', { exact: true }).focus();
  await page.keyboard.type('Invented check affiliation');
  await page.keyboard.press('Tab');
  await page.keyboard.type('Invented private reason; no team game asserted');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('article', { name: 'Review item 1' })).toBeVisible();
}
for (const width of [1672, 1440, 768, 390])
  for (const loaded of [false, true]) {
    test(`manual plan keyboard ${loaded ? 'observed' : 'Yahoo-only'} ${width}`, async ({
      page,
      context,
    }, testInfo) => {
      await page.setViewportSize({ width, height: 941 });
      const evidence = await protocol(page, loaded);
      const plan = await openPlan(page, width);
      await expect(plan.getByText(/20 minutes/)).toBeVisible();
      await createItem(page);
      const item = page.getByRole('article', { name: 'Review item 1' });
      await expect(item.getByText('fabricated-plan-1', { exact: true })).toBeVisible();
      await expect(item.getByText(/Schedule coverage unavailable/)).toBeVisible();
      await keyboardButton(page, 'Edit item 1');
      await expect(page.getByLabel('Review action', { exact: true })).toBeFocused();
      await expect(
        page.getByRole('combobox', { name: 'Returned player', exact: true }),
      ).toBeDisabled();
      await page.getByLabel('Review action', { exact: true }).fill('Invented verify assignment');
      await page.getByLabel('Review date', { exact: true }).fill('2027-01-02');
      await keyboardButton(page, 'Save review item');
      await keyboardButton(page, 'Mark item 1 reviewed');
      await expect(item.getByText('Reviewed', { exact: true })).toBeVisible();
      await expect(item.getByText(/Schedule coverage unavailable/)).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({
        path: testInfo.outputPath(`manual-plan-${loaded}-${width}.png`),
        fullPage: true,
      });
      await page.addScriptTag({ url: '/axe-check.js' });
      expect(
        await page.evaluate(
          async () =>
            (await window.axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa'] }))
              .violations,
        ),
      ).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
      await keyboardButton(page, 'Return item 1 to pending');
      await keyboardButton(page, 'Next week');
      await page.getByRole('searchbox').fill('hide every player');
      await expect(item.getByText('2027-01-02', { exact: true })).toBeVisible();
      await keyboardButton(page, 'Reopen player for item 1');
      await expect(
        page.getByRole('heading', { name: 'Invented Same Name', level: 1, exact: true }),
      ).toBeVisible();
      await expect(page.getByText('fabricated-plan-1', { exact: true })).toBeVisible();
      expect(page.url()).toMatch(/#profile$/);
      expect(await page.evaluate(() => JSON.stringify(history.state))).not.toContain(
        'fabricated-plan-1',
      );
      await page.goBack();
      await keyboardButton(page, 'Manual plan');
      await expect(item.getByText('Invented verify assignment', { exact: true })).toBeVisible();
      await navigate(page, width, '03 My Roster');
      await keyboardButton(page, 'Fantasy Points');
      await openPlan(page, width);
      await expect(item.getByText('fabricated-plan-1', { exact: true })).toBeVisible();
      await keyboardButton(page, 'Remove item 1');
      await expect(page.getByRole('article')).toHaveCount(0);
      await keyboardButton(page, 'Record no action needed');
      await expect(plan.getByText('No action needed acknowledged.', { exact: true })).toBeVisible();
      await keyboardButton(page, 'Return review to pending');
      await expect(plan.getByText('Review pending.', { exact: true })).toBeVisible();
      const persisted = await page.evaluate(() => ({
        local: localStorage.length,
        session: sessionStorage.length,
        cookie: document.cookie,
        history: JSON.stringify(history.state),
        url: location.href,
      }));
      expect(persisted.local).toBe(0);
      expect(persisted.session).toBe(0);
      expect(persisted.cookie).toBe('');
      expect(await context.cookies()).toEqual([]);
      for (const text of [
        'fabricated-plan-1',
        'Invented verify assignment',
        'Invented private reason',
        'fabricated-plan-capability',
      ]) {
        expect(JSON.stringify(persisted)).not.toContain(text);
        expect(JSON.stringify(evidence.requests)).not.toContain(text);
        expect(JSON.stringify(evidence.logs)).not.toContain(text);
      }
      expect(
        evidence.requests.every(
          ({ url, body }) =>
            new URL(url).origin === 'http://127.0.0.1:4173' &&
            !new URL(url).search &&
            body === null,
        ),
      ).toBe(true);
      expect(evidence.external).toEqual([]);
      expect(evidence.logs).toEqual([]);
    });
  }

for (const boundary of [
  'source replacement',
  'session replacement',
  'disconnect',
  'expiry',
  'server restart',
  'reload',
]) {
  test(`manual plan discarded on ${boundary}`, async ({ page }) => {
    const evidence = await protocol(page, false);
    await openPlan(page, 1672);
    await createItem(page);
    await keyboardButton(page, 'Record no action needed');
    if (boundary === 'source replacement') {
      evidence.replace();
      await page.evaluate(() => window.dispatchEvent(new Event('focus')));
      await expect(page.getByRole('article')).toHaveCount(0);
    } else if (boundary === 'disconnect') {
      await navigate(page, 1672, '06 Connections');
      await keyboardButton(page, 'Disconnect local session');
      await expect(
        page.getByRole('heading', { name: 'Private session unavailable' }),
      ).toBeVisible();
    } else if (boundary === 'expiry') {
      evidence.expire();
      await page.evaluate(() => window.dispatchEvent(new Event('focus')));
      await expect(
        page.getByRole('heading', { name: 'Private session unavailable' }),
      ).toBeVisible();
      evidence.reopen();
    } else if (boundary === 'server restart') {
      await page.route('**/api/view', (route) =>
        route.fulfill({ status: 401, json: { error: 'Session unavailable' } }),
      );
      await page.evaluate(() => window.dispatchEvent(new Event('focus')));
      await expect(
        page.getByRole('heading', { name: 'Private session unavailable' }),
      ).toBeVisible();
      await page.unroute('**/api/view');
      await page.route('**/api/view', (route) => route.fulfill({ json: observation(false) }));
    } else if (boundary === 'reload') {
      await page.reload();
      await expect(
        page.getByRole('heading', { name: 'Private session unavailable' }),
      ).toBeVisible();
    }
    if (boundary !== 'source replacement') {
      await page.goto('/#access=fabricated-reopened-capability-12345678901234567890');
      await expect(page.locator('.screen-content')).toHaveAttribute('data-source', 'private');
    }
    const plan = await openPlan(page, 1672);
    await expect(plan.getByRole('article')).toHaveCount(0);
    await expect(plan.getByText('Review pending.', { exact: true })).toBeVisible();
    await page.goBack();
    await expect(
      page.getByText('Invented private reason; no team game asserted', { exact: true }),
    ).toHaveCount(0);
    await page.goForward();
    await expect(page.getByRole('article')).toHaveCount(0);
  });
}
