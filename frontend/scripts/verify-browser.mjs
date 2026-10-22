import { browserOrigin, browserPort } from './browser-server.mjs';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { preview } from 'vite';

const require = createRequire(import.meta.url);
const output = new URL('../output/playwright/', import.meta.url);
await mkdir(output, { recursive: true });
const server = await preview({
  preview: { host: '127.0.0.1', port: browserPort, strictPort: true },
});
let browser;
try {
  browser = await chromium.launch({
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    headless: true,
  });
  const page = await browser.newPage();
  const external = [];
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.route('**/*', (route) => {
    if (new URL(route.request().url()).origin === browserOrigin) return route.continue();
    external.push(route.request().url());
    return route.abort();
  });
  await page.goto(browserOrigin);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => Array.from(document.images).every((image) => image.complete));
  await page
    .locator('img')
    .evaluateAll(async (images) => Promise.all(images.map((image) => image.decode())));
  await page.waitForFunction(() => !document.querySelector('[data-image-state="loading"]'));
  assert.equal(
    await page
      .locator('img')
      .evaluateAll((images) => images.every((image) => image.naturalWidth > 0)),
    true,
    'Every local player photograph and team logo must load',
  );
  const sizes = [
    ['desktop', 1672, 941],
    ['laptop', 1440, 900],
    ['tablet', 768, 1024],
    ['mobile', 390, 844],
  ];
  for (const [name, width, height] of sizes) {
    await page.setViewportSize({ width, height });
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth),
      width,
      `${name}: page must not overflow horizontally`,
    );
    await page.screenshot({
      path: fileURLToPath(new URL(`overview-${name}.png`, output)),
      fullPage: name !== 'desktop',
    });
    await page.getByRole('tab', { name: /Goalies/ }).click();
    await page
      .getByRole('button', { name: 'Inspect Demo Goalie', exact: true })
      .waitFor({ state: 'visible' });
    await page.keyboard.press('ArrowRight');
    await page.locator('#roster-tab-injured[aria-selected="true"]').waitFor();
    assert.equal(
      await page.getByRole('tab', { name: /Injured \(2\)/ }).getAttribute('aria-selected'),
      'true',
    );
    const roster = page.getByRole('table', { name: 'My roster' });
    assert.equal(await roster.getByRole('row').count(), 3, `${name}: two reported injury examples`);
    await roster
      .getByRole('button', { name: 'Inspect Demo Forward', exact: true })
      .waitFor({ state: 'visible' });
    if (name === 'desktop' || name === 'mobile')
      await page.screenshot({
        path: fileURLToPath(new URL(`overview-injured-${name}.png`, output)),
        fullPage: name !== 'desktop',
      });
    await page.getByRole('tab', { name: /Forwards/ }).click();
    await roster
      .getByRole('button', { name: 'Inspect Nathan MacKinnon', exact: true })
      .waitFor({ state: 'visible' });
    assert.equal(
      await roster.getByRole('button', { name: 'Inspect Demo Forward', exact: true }).count(),
      1,
      'Injured players retain positional membership',
    );
    await page.getByRole('tab', { name: /All Players/ }).click();
    await roster
      .getByRole('button', { name: 'Inspect Cale Makar', exact: true })
      .waitFor({ state: 'visible' });
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth),
      width,
      `${name}: injury navigation must not create page overflow`,
    );
  }
  await page.setViewportSize({ width: 1672, height: 941 });
  const monday = page.getByRole('article', { name: 'Monday, December 7' });
  await monday.getByRole('button', { name: /3 more games/ }).click();
  assert.equal(await monday.getByRole('listitem').count(), 6);
  await monday.getByRole('button', { name: /Show fewer/ }).click();
  await page.getByRole('searchbox').fill('bouchard');
  await page.getByRole('button', { name: 'Inspect Evan Bouchard', exact: true }).click();
  assert.equal(
    await page
      .getByRole('complementary', { name: 'Player inspection' })
      .getByRole('heading', { name: 'Evan Bouchard' })
      .count(),
    1,
  );
  await page.getByRole('searchbox').fill('');
  await page.getByRole('tab', { name: 'Game log', exact: true }).click();
  assert.equal(await page.getByRole('heading', { name: 'Game log unavailable' }).count(), 1);
  await page.getByRole('button', { name: 'Next week', exact: true }).click();
  assert.equal(
    await page
      .getByRole('region', { name: 'Weekly schedule' })
      .getByText('Unknown', { exact: true })
      .count(),
    7,
  );
  await page.getByRole('button', { name: 'DEMO WEEK', exact: true }).click();
  await page.getByRole('button', { name: 'Inspect Cale Makar', exact: true }).click();
  await page.getByRole('button', { name: 'Data notes', exact: true }).click();

  await page.getByRole('button', { name: 'Image credits', exact: true }).click();
  assert.equal(
    await page
      .getByRole('region', { name: 'Image credits' })
      .getByRole('link', { name: 'Cale Makar' })
      .count(),
    1,
  );
  await page.getByRole('button', { name: 'Image credits', exact: true }).click();
  assert.equal(await page.getByRole('region', { name: 'Data certainty notes' }).isVisible(), true);
  await page.getByRole('button', { name: 'Data notes', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
  assert.equal(
    await page.getByRole('button', { name: 'Close navigation', exact: true }).isVisible(),
    true,
  );
  await page.getByRole('button', { name: 'Close navigation', exact: true }).click();

  const axeSource = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');
  await page.route(`${browserOrigin}/axe-check.js`, (route) =>
    route.fulfill({ contentType: 'application/javascript', body: axeSource }),
  );
  await page.addScriptTag({ url: `${browserOrigin}/axe-check.js` });
  const accessibility = [];
  for (const width of [1672, 390]) {
    await page.setViewportSize({ width, height: 941 });
    const result = await page.evaluate(async () =>
      window.axe.run(document, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
      }),
    );
    accessibility.push({ width, violations: result.violations });
  }
  await writeFile(new URL('accessibility.json', output), JSON.stringify(accessibility, null, 2));
  assert.deepEqual(
    accessibility.flatMap((result) =>
      result.violations.map((v) => ({
        width: result.width,
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => n.target),
      })),
    ),
    [],
    'Accessibility violations',
  );
  assert.deepEqual(external, [], 'The fixture Overview must make no external requests');
  assert.deepEqual(errors, [], 'Browser console must have no errors');
  await writeFile(
    new URL('verification.json', output),
    JSON.stringify(
      {
        viewports: sizes,
        externalRequests: external,
        consoleErrors: errors,
        interactions: 'passed',
        accessibility: 'passed',
      },
      null,
      2,
    ),
  );
  console.log(
    'Browser checks passed: four widths, fixture interactions, zero external requests, zero console errors, axe WCAG A/AA checks.',
  );
} finally {
  await browser?.close();
  await new Promise((resolve, reject) =>
    server.httpServer.close((error) => (error ? reject(error) : resolve())),
  );
}
