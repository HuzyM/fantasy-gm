import { browserOrigin } from '../scripts/browser-server.mjs';
import { test, expect } from 'playwright/test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');

// Fabricated local protocol responses only; no provider access is authorized.
const fixture = (id, time, changes = {}) => ({
  id,
  time,
  away: 'BOS',
  home: 'TOR',
  state: 'SCHEDULED',
  upcomingEligible: true,
  ...changes,
});
const response = () => ({
  mode: 'private',
  source: 'yahoo',
  provenance: ['SYNTHETIC PROTOCOL TEST ONLY'],
  league: { name: 'Invented league', season: 2026 },
  roster: {
    teamName: 'Invented team',
    returnedCount: 3,
    contextUnverified: true,
    coverage: { kind: null, date: null, week: null },
    entries: [
      {
        id: 'invented-one',
        name: 'Invented One',
        positions: ['C', 'LW'],
        slot: 'BN',
        team: 'TOR',
        affiliationUnverified: false,
        scheduleStatus: 'MATCHED',
      },
      {
        id: 'invented-two',
        name: 'Invented Two',
        positions: ['D'],
        slot: 'D',
        team: 'TOR',
        affiliationUnverified: false,
        scheduleStatus: 'MATCHED',
      },
      {
        id: 'invented-unknown',
        name: 'Invented Unknown',
        positions: null,
        slot: null,
        team: null,
        affiliationUnverified: true,
        scheduleStatus: 'UNSUPPORTED_TEAM',
      },
    ],
  },
  schedule: {
    start: '2026-11-01',
    end: '2026-11-07',
    timezone: 'America/Toronto',
    observedAt: '2026-11-01T04:00:00Z',
    issues: ['COVERAGE_UNVERIFIED'],
    teams: [],
    days: [
      {
        date: '2026-11-01',
        count: { state: 'incomplete', value: 6, reason: 'Fabricated partial observation' },
        games: [
          fixture('first', '2026-11-01T05:30:00Z'),
          fixture('first', '2026-11-01T05:30:00Z'),
          fixture('repeated-hour', '2026-11-01T06:30:00Z', { away: 'TOR', home: 'MTL' }),
          fixture('complete', '2026-11-01T08:00:00Z', {
            state: 'COMPLETED',
            upcomingEligible: false,
          }),
          fixture('undated', null),
        ],
      },
      {
        date: '2026-11-02',
        count: { state: 'incomplete', value: 3, reason: 'Fabricated partial observation' },
        games: [
          fixture('second-date', '2026-11-03T00:00:00Z'),
          fixture('conflict', '2026-11-03T01:00:00Z'),
          fixture('conflict', '2026-11-03T01:00:00Z', {
            state: 'CANCELLED',
            upcomingEligible: false,
          }),
        ],
      },
    ],
  },
});

for (const width of [1672, 390]) {
  test(`weekly roster observations ${width}`, async ({ page }, testInfo) => {
    const errors = [],
      external = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text());
    });
    await page.clock.install({ time: new Date('2026-11-05T12:00:00Z') });
    await page.route('**/*', (route) => {
      if (new URL(route.request().url()).origin === browserOrigin) return route.continue();
      external.push(route.request().url());
      return route.abort();
    });
    await page.route('**/axe-check.js', (route) =>
      route.fulfill({ contentType: 'application/javascript', body: axe }),
    );
    await page.route('**/api/status', (route) =>
      route.fulfill({ json: { mode: 'private', yahoo: 'loaded', schedule: 'observed' } }),
    );
    await page.route('**/api/view', (route) => route.fulfill({ json: response() }));
    await page.setViewportSize({ width, height: 941 });
    await page.goto('/#access=synthetic-roster-week-capability-12345678901234567890');
    await expect(
      page.getByRole('button', { name: 'Inspect Invented One', exact: true }),
    ).toBeVisible();
    if (width < 900)
      await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
    await page.getByRole('button', { name: '02 Schedule Planner', exact: true }).click();
    await expect(page.getByRole('table', { name: 'Daily matchups', exact: true })).toBeVisible();
    await page.getByRole('tab', { name: 'Daily matchups', exact: true }).focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: 'Roster week', exact: true })).toBeFocused();
    const table = page.getByRole('table', { name: 'Weekly roster schedule', exact: true });
    await expect(table.getByRole('columnheader')).toHaveCount(10);
    for (const name of ['Invented One', 'Invented Two']) {
      const row = table.getByRole('row', { name: new RegExp(name) });
      await expect(
        row.getByRole('cell', { name: '3 observed; total unknown', exact: true }),
      ).toHaveCount(1);
      await expect(
        row.getByRole('cell', { name: '1 date pair observed', exact: true }),
      ).toHaveCount(1);
      await expect(
        row.getByText('Schedule anomaly: multiple scheduled team games observed on this date.'),
      ).toHaveCount(1);
      await expect(row.getByText('Back-to-back', { exact: true })).toHaveCount(2);
      await expect(row.getByText(/conflicting observation/)).toHaveCount(2);
      await expect(row.getByText(/date\/time unverified/)).toBeVisible();
    }
    await expect(table.getByRole('row', { name: /Invented Unknown/ })).toContainText(
      'Join unavailable',
    );
    await expect(page.getByText(/Reported affiliations may be stale/)).toHaveCount(2);
    await page.addScriptTag({ url: '/axe-check.js' });
    const violations = await page.evaluate(async () =>
      (
        await window.axe.run(document, {
          runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
        })
      ).violations.map((v) => v.id),
    );
    expect(violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    const scroll = page.getByRole('region', {
      name: 'Scrollable weekly roster schedule',
      exact: true,
    });
    const viewportWidth = await scroll.evaluate((node) => node.clientWidth);
    const playerWidth = await table
      .getByRole('columnheader')
      .first()
      .evaluate((node) => node.getBoundingClientRect().width);
    expect(playerWidth).toBeLessThanOrEqual(width === 390 ? 160 : 220);
    expect(playerWidth).toBeLessThan(viewportWidth * 0.6);
    if (width === 390) {
      await scroll.focus();
      await page.keyboard.press('ArrowRight');
      await expect.poll(() => scroll.evaluate((node) => node.scrollLeft)).toBeGreaterThan(0);
      const visibleFixture = table
        .getByRole('row', { name: /Invented One/ })
        .getByRole('cell')
        .nth(1)
        .getByText('vs BOS', { exact: true })
        .first();
      await visibleFixture.scrollIntoViewIfNeeded();
      expect(
        await visibleFixture.evaluate((node) => {
          const fixture = node.getBoundingClientRect();
          const table = node.closest('table');
          const player = table.querySelector('tbody th').getBoundingClientRect();
          const viewport = table.parentElement.getBoundingClientRect();
          return Math.min(fixture.right, viewport.right) - Math.max(fixture.left, player.right);
        }),
      ).toBeGreaterThan(30);
    }
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: testInfo.outputPath(`roster-week-${width}.png`),
      fullPage: true,
    });
    await page
      .getByRole('combobox', { name: 'Position eligibility', exact: true })
      .selectOption('LW');
    await expect(table.getByRole('row')).toHaveCount(2);
    await page
      .getByRole('combobox', { name: 'Reported roster slot', exact: true })
      .selectOption('Unknown');
    await expect(
      page.getByText('No roster players match these filters.', { exact: true }),
    ).toBeVisible();
    await page
      .getByRole('combobox', { name: 'Position eligibility', exact: true })
      .selectOption('Unknown');
    await expect(table.getByRole('row', { name: /Invented Unknown/ })).toBeVisible();
    await page
      .getByRole('combobox', { name: 'Position eligibility', exact: true })
      .selectOption('all');
    await page
      .getByRole('combobox', { name: 'Reported roster slot', exact: true })
      .selectOption('all');
    await page.getByRole('button', { name: 'Next week', exact: true }).click();
    await expect(table.getByText('Coverage unknown', { exact: true })).toHaveCount(14);
    await page.getByRole('button', { name: 'Loaded window', exact: true }).click();
    await expect(table.getByRole('columnheader', { name: 'Sun Nov 1', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'View Invented One profile', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Upcoming Observed Team Games', exact: true }),
    ).toBeVisible();
    await expect(page.locator('.profile-game')).toHaveCount(0);
    expect(external).toEqual([]);
    expect(errors).toEqual([]);
    expect(
      await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie]),
    ).toEqual([0, 0, '']);
    expect(new URL(page.url()).hash).not.toContain('invented-one');
  });
}
