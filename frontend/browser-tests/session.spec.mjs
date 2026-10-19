import { test, expect } from 'playwright/test';
// Synthetic protocol inputs only. Never run the human private launcher in automation.
const view = {
  mode: 'private',
  source: 'yahoo',
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
    await page.getByRole('button', { name: '06 Connections', exact: true }).click();
    await page.getByRole('button', { name: 'Disconnect local session', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Private session unavailable', exact: true }),
    ).toBeVisible();
    await expect(page.getByText('Synthetic Protocol Player', { exact: true })).toHaveCount(0);
    await expect(page.getByText('Cale Makar', { exact: true })).toHaveCount(0);
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
