import { test, expect } from 'playwright/test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');

// Fabricated local protocol only: no authentication, provider or private session.
test.use({ timezoneId: 'Asia/Tokyo' });
function observation(loaded, count = 2) {
  return {
    mode: 'private',
    source: 'yahoo',
    provenance: ['FABRICATED WINDOW PROTOCOL'],
    league: { name: 'Invented league', season: 2026 },
    planningWindow: { start: '2026-12-31', end: '2027-01-06', timezone: 'America/Toronto' },
    roster: {
      teamName: 'Invented team',
      returnedCount: count,
      contextUnverified: true,
      coverage: { kind: null, date: null, week: null },
      entries: ['First', 'Second'].slice(0, count).map((name, index) => ({
        id: `fabricated-window-${index}`,
        name: `Invented ${name}`,
        positions: ['C'],
        slot: 'C',
        team: index ? 'MTL' : 'TOR',
        affiliationUnverified: false,
        scheduleStatus: loaded ? 'MATCHED' : 'UNAVAILABLE',
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
async function protocol(page, view) {
  const external = [],
    api = [],
    errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/'))
      api.push(new URL(request.url()).pathname);
  });
  await page.clock.setFixedTime(new Date('2030-07-01T02:30:00Z'));
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
        yahoo: 'loaded',
        schedule: view.schedule ? 'observed' : 'unavailable',
      },
    }),
  );
  await page.route('**/api/view', (route) => route.fulfill({ json: view }));
  await page.goto('/#access=synthetic-window-capability-12345678901234567890');
  await expect(page.locator('.screen-content')).toHaveAttribute('data-source', 'private');
  return { external, api, errors };
}

for (const width of [1672, 390])
  for (const loaded of [false, true]) {
    test(`explicit ${loaded ? 'loaded' : 'Yahoo-only'} window ${width}`, async ({
      page,
      context,
    }, testInfo) => {
      await page.setViewportSize({ width, height: 941 });
      const { external, api, errors } = await protocol(page, observation(loaded));
      async function navigate(name) {
        if (width < 900)
          await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
        await page.getByRole('button', { name, exact: true }).click();
      }
      const before = api.length;
      await navigate('04 Compare Players');
      await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toHaveAttribute(
        'aria-selected',
        'true',
      );
      const week = page.getByRole('region', { name: 'Weekly game comparison' });
      await expect(week.getByText('Dec 31 – Jan 6, 2027', { exact: true })).toBeVisible();
      await expect(week.getByRole('heading', { level: 3 })).toHaveCount(7);
      await expect(
        week.getByText(loaded ? 'Shared game dates: 1' : 'Shared game dates: Unknown', {
          exact: true,
        }),
      ).toBeVisible();
      if (loaded) await expect(week.getByText('7:30 PM EST', { exact: true })).toHaveCount(2);
      await page.getByRole('button', { name: 'Swap players', exact: true }).click();
      await expect(page.getByRole('combobox', { name: 'First player', exact: true })).toHaveValue(
        'fabricated-window-1',
      );
      await page.getByRole('button', { name: 'Next comparison week', exact: true }).click();
      await expect(week.getByText('Jan 7 – Jan 13, 2027', { exact: true })).toBeVisible();
      await expect(
        week.getByText(loaded ? 'Coverage unknown' : 'Join unavailable', { exact: true }),
      ).toHaveCount(14);
      await navigate('02 Schedule Planner');
      await expect(page.getByText('Dec 31 – Jan 6, 2027', { exact: true })).toBeVisible();
      await expect(
        page.getByRole('region', { name: 'Planner week' }).getByRole('button'),
      ).toHaveCount(7);
      await expect(page.getByText(/Planning window: 2026-12-31 – 2027-01-06/)).toBeVisible();
      if (width === 390) {
        expect(
          await page
            .locator('.planner-day strong')
            .filter({ hasText: 'Unknown' })
            .evaluateAll((labels) =>
              labels.every((label) => {
                const range = document.createRange();
                range.selectNodeContents(label);
                const lines = Array.from(range.getClientRects());
                const card = label.closest('button').getBoundingClientRect();
                return (
                  lines.length === 1 && lines[0].left >= card.left && lines[0].right <= card.right
                );
              }),
            ),
        ).toBe(true);
      }
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({
        path: testInfo.outputPath(`explicit-planner-${loaded}-${width}.png`),
        fullPage: true,
      });
      await page.getByLabel('Choose date', { exact: true }).fill('2027-01-08');
      await expect(page.getByText('Jan 8 – Jan 14, 2027', { exact: true })).toBeVisible();
      await page.getByRole('button', { name: 'Compare players', exact: true }).click();
      await expect(week.getByText('Jan 8 – Jan 14, 2027', { exact: true })).toBeVisible();
      await page.getByRole('tab', { name: 'Statistics', exact: true }).focus();
      await page.keyboard.press('ArrowRight');
      await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toBeFocused();
      expect(api.length).toBe(before);
      expect(external).toEqual([]);
      expect(errors).toEqual([]);
      expect(new URL(page.url()).hash).toBe('#comparison');
      expect(JSON.stringify(await page.evaluate(() => history.state))).not.toMatch(
        /2027|Invented|fabricated-window/,
      );
      expect(
        await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie]),
      ).toEqual([0, 0, '']);
      expect(await context.cookies()).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
      await page.addScriptTag({ url: '/axe-check.js' });
      expect(
        await page.evaluate(async () =>
          (
            await window.axe.run(document, {
              runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
            })
          ).violations.map((v) => v.id),
        ),
      ).toEqual([]);
      await page.screenshot({
        path: testInfo.outputPath(`explicit-comparison-${loaded}-${width}.png`),
        fullPage: true,
      });
    });
  }

for (const count of [0, 1])
  test(`explicit Yahoo-only comparison requires two identities: ${count}`, async ({ page }) => {
    const { external } = await protocol(page, observation(false, count));
    await page.getByRole('button', { name: '04 Compare Players', exact: true }).click();
    await expect(
      page.getByText(
        count
          ? 'At least two supplied players are required to compare.'
          : 'No players are available to compare.',
        { exact: true },
      ),
    ).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toHaveCount(0);
    await expect(page.getByText('Auston Matthews', { exact: true })).toHaveCount(0);
    expect(external).toEqual([]);
  });
