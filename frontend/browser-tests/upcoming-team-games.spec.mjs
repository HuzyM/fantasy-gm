import { test, expect } from 'playwright/test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');

// Entirely fabricated protocol input. Never authorize a real provider in automation.
for (const width of [1672, 390]) {
  test(`upcoming observed team games ${width}`, async ({ page }, testInfo) => {
    const external = [];
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.clock.install({ time: new Date('2026-11-01T05:00:00Z') });
    await page.route('**/*', (route) => {
      if (new URL(route.request().url()).origin === 'http://127.0.0.1:4173')
        return route.continue();
      external.push(route.request().url());
      return route.abort();
    });
    await page.route('**/axe-check.js', (r) =>
      r.fulfill({ contentType: 'application/javascript', body: axe }),
    );
    await page.route('**/api/status', (r) =>
      r.fulfill({ json: { mode: 'private', yahoo: 'loaded', schedule: 'observed' } }),
    );
    await page.route('**/api/view', (r) =>
      r.fulfill({
        json: {
          mode: 'private',
          source: 'yahoo',
          provenance: ['SYNTHETIC PROTOCOL TEST ONLY'],
          league: { name: 'Invented league', season: 2026 },
          roster: {
            teamName: 'Invented team',
            returnedCount: 2,
            contextUnverified: true,
            coverage: { kind: null, date: null, week: null },
            entries: [
              {
                id: 'invented-one',
                name: 'Invented One',
                positions: ['D'],
                slot: 'D',
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
                affiliationUnverified: true,
                scheduleStatus: 'AFFILIATION_UNVERIFIED',
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
                count: { state: 'incomplete', value: 3, reason: 'Synthetic partial coverage' },
                games: [
                  {
                    id: 'later',
                    away: 'BOS',
                    home: 'TOR',
                    time: '2026-11-01T06:30:00Z',
                    state: 'SCHEDULED',
                    upcomingEligible: true,
                  },
                  {
                    id: 'first',
                    away: 'TOR',
                    home: 'MTL',
                    time: '2026-11-01T05:30:00Z',
                    state: 'SCHEDULED',
                    upcomingEligible: true,
                  },
                  {
                    id: 'completed',
                    away: 'EDM',
                    home: 'TOR',
                    time: '2026-11-01T08:00:00Z',
                    state: 'COMPLETED',
                    upcomingEligible: false,
                  },
                ],
              },
            ],
          },
        },
      }),
    );
    await page.setViewportSize({ width, height: 941 });
    await page.goto('/#access=synthetic-upcoming-capability-12345678901234567890');
    await expect(
      page.getByRole('button', { name: 'Inspect Invented One', exact: true }),
    ).toBeVisible();
    const navigate = async (name) => {
      if (width < 900)
        await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
      await page.getByRole('button', { name, exact: true }).click();
    };
    const capture = async (screen) => {
      await page.evaluate(() => document.fonts.ready);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
      await page.addScriptTag({ url: '/axe-check.js' });
      const violations = await page.evaluate(
        async () =>
          (
            await window.axe.run(document, {
              runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
            })
          ).violations,
      );
      expect(violations.map((v) => v.id)).toEqual([]);
      await page.screenshot({
        path: testInfo.outputPath(`${screen}-${width}.png`),
        fullPage: true,
      });
    };
    await navigate('03 My Roster');
    const rows = page.getByRole('table', { name: 'My roster', exact: true });
    await expect(rows.getByRole('cell', { name: /@ MTL · Nov 1, 1:30 AM ET/ })).toBeVisible();
    await expect(
      rows.getByRole('cell', { name: 'Unknown Schedule or affiliation unavailable', exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/Reported affiliations may be stale/)).toBeVisible();
    await capture('roster');
    await page.getByRole('button', { name: 'View Full Player Profile →', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Upcoming Observed Team Games', exact: true }),
    ).toBeVisible();
    await expect(page.locator('.profile-game')).toHaveCount(2);
    await expect(page.locator('.profile-game').first()).toContainText('@ MTL');
    await capture('profile');
    await page.getByRole('button', { name: 'View Schedule →', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Schedule Planner', exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole('table', { name: 'Daily matchups' }).getByText('COMPLETED', { exact: true }),
    ).toBeVisible();
    await capture('planner');
    expect(external).toEqual([]);
    expect(errors).toEqual([]);
    expect(
      await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie]),
    ).toEqual([0, 0, '']);
  });
}
