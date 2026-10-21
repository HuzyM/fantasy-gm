import { test, expect } from 'playwright/test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');

// Fabricated local protocol observations only; this never opens a provider session.
const response = (replacement = false) => ({
  mode: 'private',
  source: 'yahoo',
  provenance: ['SYNTHETIC PROTOCOL TEST ONLY'],
  league: { name: 'Invented comparison league', season: 2026 },
  roster: {
    teamName: 'Invented comparison team',
    returnedCount: 2,
    contextUnverified: true,
    coverage: { kind: null, date: null, week: null },
    entries: ['First', 'Second'].map((name, index) => ({
      id: `${replacement ? 'replacement' : 'invented'}-${index}`,
      name: `${replacement ? 'Replacement' : 'Invented'} ${name}`,
      positions: ['C'],
      slot: 'C',
      team: index ? 'MTL' : 'TOR',
      affiliationUnverified: false,
      scheduleStatus: 'MATCHED',
    })),
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
        count: { state: 'incomplete', value: 3, reason: 'Synthetic partial observation' },
        games: [
          {
            id: 'head-to-head',
            away: 'MTL',
            home: 'TOR',
            time: '2026-11-01T05:30:00Z',
            state: 'SCHEDULED',
            upcomingEligible: true,
          },
          {
            id: 'repeat-hour',
            away: 'MTL',
            home: 'TOR',
            time: '2026-11-01T06:30:00Z',
            state: 'SCHEDULED',
            upcomingEligible: true,
          },
          {
            id: 'excluded',
            away: 'BOS',
            home: 'TOR',
            time: null,
            state: 'CANCELLED',
            upcomingEligible: false,
          },
        ],
      },
    ],
  },
});

test('weekly game comparison preserves unavailable source eligibility and excludes unqualified games', async ({
  page,
}) => {
  const observation = response();
  observation.schedule.days.push(
    {
      date: '2026-11-02',
      count: { state: 'incomplete', value: 2, reason: 'Synthetic partial observation' },
      games: [
        {
          id: 'eligibility-omitted',
          away: 'BOS',
          home: 'TOR',
          time: '2026-11-03T00:00:00Z',
          state: 'SCHEDULED',
        },
        {
          id: 'second-monday',
          away: 'NYR',
          home: 'MTL',
          time: '2026-11-03T00:00:00Z',
          state: 'SCHEDULED',
          upcomingEligible: true,
        },
      ],
    },
    {
      date: '2026-11-03',
      count: { state: 'incomplete', value: 2, reason: 'Synthetic partial observation' },
      games: [
        {
          id: 'eligibility-excluded',
          away: 'BOS',
          home: 'TOR',
          time: '2026-11-04T00:00:00Z',
          state: 'SCHEDULED',
          upcomingEligible: false,
        },
        {
          id: 'second-tuesday',
          away: 'NYR',
          home: 'MTL',
          time: '2026-11-04T00:00:00Z',
          state: 'SCHEDULED',
          upcomingEligible: true,
        },
      ],
    },
  );
  const external = [];
  await page.route('**/*', (route) => {
    if (new URL(route.request().url()).origin === 'http://127.0.0.1:4173') return route.continue();
    external.push(route.request().url());
    return route.abort();
  });
  await page.route('**/api/status', (route) =>
    route.fulfill({ json: { mode: 'private', yahoo: 'loaded', schedule: 'observed' } }),
  );
  await page.route('**/api/view', (route) => route.fulfill({ json: observation }));
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.goto('/#access=synthetic-comparison-capability-12345678901234567890');
  await expect(
    page.getByRole('button', { name: 'Inspect Invented First', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: '04 Compare Players', exact: true }).click();
  await page.getByRole('tab', { name: 'Schedule', exact: true }).click();
  const week = page.getByRole('region', { name: 'Weekly game comparison', exact: true });
  const missing = week.getByRole('group', {
    name: 'Invented First games on 2026-11-02',
    exact: true,
  });
  const excluded = week.getByRole('group', {
    name: 'Invented First games on 2026-11-03',
    exact: true,
  });
  await expect(
    missing.getByText('Scheduled · source eligibility unavailable', { exact: true }),
  ).toBeVisible();
  await expect(
    excluded.getByText('Scheduled · source eligibility excluded', { exact: true }),
  ).toBeVisible();
  for (const group of [missing, excluded])
    await expect(
      group.getByText('Excluded from scheduled counts and opportunities.', { exact: true }),
    ).toBeVisible();
  await expect(
    week.getByRole('region', { name: 'Invented First game summary', exact: true }).locator('dd'),
  ).toHaveText(['2', '0']);
  await expect(
    week.getByRole('region', { name: 'Invented Second game summary', exact: true }).locator('dd'),
  ).toHaveText(['4', '2']);
  await expect(week.getByText('Shared game dates: 1', { exact: true })).toBeVisible();
  await expect(week.getByText('Shared game date', { exact: true })).toHaveCount(1);
  expect(external).toEqual([]);
});

for (const [size, width, height] of [
  ['desktop', 1672, 941],
  ['laptop', 1440, 900],
  ['tablet', 768, 1024],
  ['mobile', 390, 844],
]) {
  test(`weekly game comparison ${size}`, async ({ page, context }, testInfo) => {
    const external = [],
      errors = [],
      api = [];
    let available = true,
      replacement = false;
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('request', (request) => {
      if (new URL(request.url()).pathname.startsWith('/api/'))
        api.push(new URL(request.url()).pathname);
    });
    await page.clock.install({ time: new Date('2026-12-05T12:00:00Z') });
    await page.addInitScript(() => {
      window.recordedHistory = [];
      for (const method of ['pushState', 'replaceState']) {
        const original = history[method].bind(history);
        history[method] = (state, unused, url) => {
          window.recordedHistory.push({ state, url });
          return original(state, unused, url);
        };
      }
    });
    await page.route('**/*', (route) => {
      if (new URL(route.request().url()).origin === 'http://127.0.0.1:4173')
        return route.continue();
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
          yahoo: available ? 'loaded' : 'unavailable',
          schedule: 'observed',
        },
      }),
    );
    await page.route('**/api/view', (route) => route.fulfill({ json: response(replacement) }));
    await page.route('**/api/disconnect', (route) =>
      route.fulfill({ json: { disconnected: true } }),
    );
    await page.setViewportSize({ width, height });
    await page.goto('/#access=synthetic-comparison-capability-12345678901234567890');
    await expect(
      page.getByRole('button', { name: 'Inspect Invented First', exact: true }),
    ).toBeVisible();
    async function navigate(name) {
      if (width < 900)
        await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
      await page.getByRole('button', { name, exact: true }).click();
    }
    await navigate('04 Compare Players');
    await page.getByRole('tab', { name: 'Statistics', exact: true }).focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toBeFocused();
    const week = page.getByRole('region', { name: 'Weekly game comparison', exact: true });
    await expect(week.getByText('Nov 1 – Nov 7, 2026', { exact: true })).toBeVisible();
    await expect(week.getByRole('heading', { level: 3 })).toHaveCount(7);
    await expect(week.getByText('Shared game date', { exact: true })).toHaveCount(1);
    await expect(week.getByText(/CANCELLED/)).toBeVisible();
    const first = week.getByRole('group', {
      name: 'Invented First games on 2026-11-01',
      exact: true,
    });
    const second = week.getByRole('group', {
      name: 'Invented Second games on 2026-11-01',
      exact: true,
    });
    await expect(first.getByText('1:30 AM EDT', { exact: true })).toBeVisible();
    await expect(first.getByText('1:30 AM EST', { exact: true })).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(() => Array.from(document.images).every((image) => image.complete));
    await page.waitForFunction(() => !document.querySelector('[data-image-state="loading"]'));
    await page.screenshot({
      path: testInfo.outputPath(`comparison-schedule-${size}.png`),
      fullPage: true,
    });
    const a = await first.boundingBox(),
      b = await second.boundingBox();
    if (width === 390) {
      expect(a.width).toBeGreaterThan(230);
      expect(b.y).toBeGreaterThan(a.y + a.height - 1);
      expect(Math.abs(a.x - b.x)).toBeLessThan(1);
    } else {
      expect(Math.abs(a.y - b.y)).toBeLessThan(1);
      expect(b.x).toBeGreaterThan(a.x + a.width - 1);
    }
    expect(
      await page.evaluate(() =>
        Array.from(document.querySelectorAll('main *'))
          .filter((node) => {
            // Portraits intentionally extend beyond their clipped frame. Check
            // the visible right edge as well as the page scroll width below.
            let right = node.getBoundingClientRect().right;
            for (let parent = node.parentElement; parent; parent = parent.parentElement) {
              if (['hidden', 'clip', 'auto', 'scroll'].includes(getComputedStyle(parent).overflowX))
                right = Math.min(right, parent.getBoundingClientRect().right);
            }
            return right > innerWidth + 1;
          })
          .map((node) => ({
            class: node.className,
            right: node.getBoundingClientRect().right,
            text: node.textContent.slice(0, 80),
          })),
      ),
    ).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    for (const text of [first, second])
      expect(await text.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
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
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: testInfo.outputPath(`comparison-schedule-${size}.png`),
      fullPage: true,
    });
    const before = api.length;
    await page.getByRole('button', { name: 'Next comparison week', exact: true }).click();
    await expect(week.getByText('Coverage unknown', { exact: true })).toHaveCount(14);
    expect(api.length).toBe(before);
    await navigate('02 Schedule Planner');
    await page.getByLabel('Choose date', { exact: true }).fill('2026-11-12');
    await page.getByRole('button', { name: 'Compare players', exact: true }).click();
    await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    await expect(week.getByText('Nov 12 – Nov 18, 2026', { exact: true })).toBeVisible();
    expect(new URL(page.url()).hash).toBe('#comparison');
    const history = JSON.stringify(await page.evaluate(() => window.recordedHistory));
    for (const privateValue of ['Invented', 'invented-', 'TOR', 'MTL', '2026-11-', 'capability'])
      expect(history).not.toContain(privateValue);
    expect(
      await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie]),
    ).toEqual([0, 0, '']);
    expect(await context.cookies()).toEqual([]);
    replacement = true;
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect(
      page.getByRole('button', { name: 'View Replacement First profile', exact: true }),
    ).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    await page.getByRole('tab', { name: 'Schedule', exact: true }).click();
    await expect(week.getByText('Nov 1 – Nov 7, 2026', { exact: true })).toBeVisible();
    await page.goBack();
    await page.goForward();
    await expect(page.getByRole('tab', { name: 'Schedule', exact: true })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    available = false;
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect(
      page.getByRole('heading', { name: 'Private session unavailable', exact: true }),
    ).toBeVisible();
    await page.goBack();
    await expect(
      page.getByRole('heading', { name: 'Private session unavailable', exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/Replacement First|Invented First/)).toHaveCount(0);
    expect(external).toEqual([]);
    expect(errors).toEqual([]);
  });
}
