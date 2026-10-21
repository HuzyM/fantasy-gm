import { test, expect } from 'playwright/test';
// Synthetic protocol inputs only. Never run the human private launcher in automation.
const view = {
  mode: 'private',
  source: 'yahoo',
  planningWindow: { start: '2026-10-19', end: '2026-10-25', timezone: 'America/Toronto' },
  provenance: ['SYNTHETIC PROTOCOL TEST — no real Yahoo information'],
  league: { name: 'Synthetic protocol league', season: 2026 },
  roster: {
    teamName: 'Synthetic protocol team',
    returnedCount: 1,
    contextUnverified: true,
    coverage: { kind: null, date: null, week: null },
    entries: [
      {
        id: 'synthetic-protocol-id',
        name: 'Synthetic Protocol Player',
        positions: ['D'],
        slot: 'IR',
        team: 'COL',
        affiliationUnverified: true,
        scheduleStatus: 'AFFILIATION_UNVERIFIED',
      },
    ],
  },
  settings: null,
  schedule: null,
};
for (const width of [1672, 390])
  test(`synthetic private protocol ${width}`, async ({ page, context }) => {
    const external = [];
    const errors = [];
    const requests = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.route('**/*', (r) => {
      if (new URL(r.request().url()).origin === 'http://127.0.0.1:4173') return r.continue();
      external.push(r.request().url());
      return r.abort();
    });
    await page.route('**/api/status', (r) =>
      r.fulfill({ json: { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' } }),
    );
    await page.route('**/api/view', (r) => {
      requests.push(r.request().headers());
      return r.fulfill({ json: view });
    });
    await page.route('**/api/disconnect', (r) => r.fulfill({ json: { disconnected: true } }));
    await page.setViewportSize({ width, height: 941 });
    await page.goto('/#access=synthetic-protocol-capability-12345678901234567890');
    await expect(
      page.getByRole('button', { name: 'Inspect Synthetic Protocol Player', exact: true }),
    ).toBeVisible();
    expect(page.url()).not.toContain('access');
    expect(
      requests.every(
        (r) => r.authorization === 'Bearer synthetic-protocol-capability-12345678901234567890',
      ),
    ).toBe(true);
    expect(requests.length).toBeGreaterThan(0);
    await expect(page.getByText('Cale Makar', { exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'View Full Player Profile →', exact: true }).click();
    expect(page.url()).toMatch(/#profile$/);
    expect(page.url()).not.toContain('synthetic-protocol-id');
    await expect(
      page.getByRole('heading', { name: 'Synthetic Protocol Player', exact: true, level: 1 }),
    ).toBeVisible();
    expect(await page.locator('.profile-portrait img').count()).toBe(0);
    expect(await page.locator('.performance-column').count()).toBe(0);
    await expect(page.getByText('No statistics supplied for this reported player.')).toBeVisible();
    await expect(page.getByText(/fictional player/)).toHaveCount(0);
    expect(
      await page.evaluate(() => ({
        local: localStorage.length,
        session: sessionStorage.length,
        cookie: document.cookie,
      })),
    ).toEqual({ local: 0, session: 0, cookie: '' });
    expect(await context.cookies()).toEqual([]);
    if (width < 900)
      await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await page.getByRole('button', { name: '03 My Roster', exact: true }).click();
    await expect(page.getByText('Returned entries', { exact: true })).toBeVisible();
    await expect(page.getByText('Roster size', { exact: true })).toHaveCount(0);
    if (width < 900)
      await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await page.getByRole('button', { name: '06 Connections', exact: true }).click();
    await expect(page.getByText(/Read-only Yahoo GETs only/)).toBeVisible();
    await page.goBack();
    await expect(page.getByRole('heading', { name: 'My Roster', level: 1 })).toBeVisible();
    await page.goBack();
    await expect(
      page.getByRole('heading', { name: 'Synthetic Protocol Player', exact: true, level: 1 }),
    ).toBeVisible();
    expect(page.url()).toMatch(/#profile$/);
    expect(await page.evaluate(() => JSON.stringify(history.state))).not.toContain(
      'synthetic-protocol-id',
    );
    await page.goForward();
    await expect(page.getByRole('heading', { name: 'My Roster', level: 1 })).toBeVisible();
    await page.goForward();
    await expect(page.getByRole('heading', { name: 'Connections', level: 1 })).toBeVisible();
    await page.getByRole('button', { name: 'Disconnect local session', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Private session unavailable', exact: true }),
    ).toBeVisible();
    await expect(page.getByText('Synthetic Protocol Player', { exact: true })).toHaveCount(0);
    await expect(page.getByText('Cale Makar', { exact: true })).toHaveCount(0);
    await page.goBack();
    await expect(
      page.getByRole('heading', { name: 'Private session unavailable', exact: true }),
    ).toBeVisible();
    await expect(page.getByText('Synthetic Protocol Player', { exact: true })).toHaveCount(0);
    await page.evaluate(() => {
      window.syntheticDocumentMarker = true;
    });
    await page.goto('/#access=synthetic-reopened-capability-12345678901234567890');
    await expect(
      page.getByRole('button', { name: 'Inspect Synthetic Protocol Player', exact: true }),
    ).toBeVisible();
    expect(await page.evaluate(() => window.syntheticDocumentMarker)).toBe(true);
    expect(page.url()).toMatch(/#overview$/);
    expect(requests.at(-1).authorization).toBe(
      'Bearer synthetic-reopened-capability-12345678901234567890',
    );
    expect(
      await page.evaluate(() => ({
        local: localStorage.length,
        session: sessionStorage.length,
        cookie: document.cookie,
      })),
    ).toEqual({ local: 0, session: 0, cookie: '' });
    await page.route('**/api/view', (r) =>
      r.fulfill({
        json: {
          ...view,
          schedule: {
            start: '2026-10-19',
            end: '2026-10-25',
            timezone: 'America/Toronto',
            observedAt: '2026-10-19T00:00:00Z',
            issues: [],
            days: [],
            teams: [],
          },
        },
      }),
    );
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    if (width < 900)
      await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await page.getByRole('button', { name: '06 Connections', exact: true }).click();
    await expect(
      page.getByText(/Read-only Yahoo GETs and public PuckAPI schedule requests only/),
    ).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    expect(external).toEqual([]);
    expect(errors).toEqual([]);
  });

test('synthetic server rotation rejects the old browser capability', async ({ page }) => {
  await page.route('**/api/status', (r) =>
    r.fulfill({ json: { mode: 'private', yahoo: 'loaded', schedule: 'unavailable' } }),
  );
  await page.route('**/api/view', (r) => r.fulfill({ json: view }));
  await page.goto('/#access=synthetic-protocol-capability-12345678901234567890');
  await expect(
    page.getByRole('button', { name: 'Inspect Synthetic Protocol Player', exact: true }),
  ).toBeVisible();
  await page.route('**/api/view', (r) =>
    r.fulfill({ status: 401, json: { error: 'Session unavailable' } }),
  );
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(
    page.getByRole('heading', { name: 'Private session unavailable', exact: true }),
  ).toBeVisible();
  await expect(page.getByText('Synthetic Protocol Player', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Cale Makar', { exact: true })).toHaveCount(0);
});

for (const [from, to] of [
  ['puckapi', 'synthetic'],
  ['synthetic', 'puckapi'],
  ['puckapi', 'puckapi'],
])
  test(`synthetic successful server rotation ${from} to ${to}`, async ({ page }) => {
    let currentView = {
      ...view,
      mode: 'synthetic',
      source: from,
      league: null,
      roster: null,
      provenance: ['Synthetic original observation'],
    };
    let reads = 0;
    await page.route('**/api/status', (r) =>
      r.fulfill({ json: { mode: 'synthetic', yahoo: 'disconnected', schedule: 'observed' } }),
    );
    await page.route('**/api/view', (r) => {
      reads += 1;
      return r.fulfill({ json: currentView });
    });
    await page.goto('/#connections');
    await expect(page.locator('.screen-content')).toHaveAttribute(
      'data-source',
      from === 'synthetic' ? 'demo' : 'public',
    );
    currentView = { ...currentView, source: to, provenance: ['Synthetic replacement observation'] };
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect.poll(() => reads).toBeGreaterThan(1);
    await expect(page.locator('.screen-content')).toHaveAttribute(
      'data-source',
      to === 'synthetic' ? 'demo' : 'public',
    );
    if (to === 'puckapi') {
      await expect(
        page.getByText('Synthetic replacement observation', { exact: true }),
      ).toBeVisible();
      await expect(page.getByText(/Read-only public PuckAPI schedule requests only/)).toBeVisible();
      await expect(page.getByText(/Read-only Yahoo GETs only/)).toHaveCount(0);
    }
    await expect(page.getByText('Synthetic original observation', { exact: true })).toHaveCount(0);
  });
