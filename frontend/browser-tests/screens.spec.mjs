import { test, expect } from 'playwright/test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');
const routes = (process.env.SCREEN_ROUTES || 'roster,profile/matthews').split(',');
const sizes = [
  ['desktop', 1672, 941],
  ['laptop', 1440, 900],
  ['tablet', 768, 1024],
  ['mobile', 390, 844],
];
for (const route of routes)
  for (const [name, width, height] of sizes) {
    test(`${route} ${name}`, async ({ page }, testInfo) => {
      const external = [];
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      page.on('console', (message) => {
        if (message.type() === 'error') errors.push(message.text());
      });
      await page.route('**/*', (r) => {
        if (new URL(r.request().url()).origin === 'http://127.0.0.1:4173') return r.continue();
        external.push(r.request().url());
        return r.abort();
      });
      await page.route('**/axe-check.js', (r) =>
        r.fulfill({ contentType: 'application/javascript', body: axe }),
      );
      await page.setViewportSize({ width, height });
      await page.goto(`/#${route}`);
      await page.evaluate(() => document.fonts.ready);
      await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete));
      await page.waitForFunction(() => !document.querySelector('[data-image-state="loading"]'));
      await page
        .locator('img')
        .evaluateAll(async (images) => Promise.all(images.map((i) => i.decode())));
      expect(
        await page.locator('img').evaluateAll((images) => images.every((i) => i.naturalWidth > 0)),
      ).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
      const imageName = `${route.replace('/', '-')}-${name}.png`;
      await page.screenshot({
        path: `output/playwright/${imageName}`,
        fullPage: true,
        animations: 'disabled',
      });
      if (process.env.VISUAL_COMPARE === '1')
        await expect(page).toHaveScreenshot(imageName, {
          fullPage: true,
          animations: 'disabled',
          maxDiffPixelRatio: 0.005,
        });
      await page.addScriptTag({ url: '/axe-check.js' });
      const violations = await page.evaluate(async () =>
        (
          await window.axe.run(document, {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
          })
        ).violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
      );
      await testInfo.attach('accessibility', {
        body: JSON.stringify(violations),
        contentType: 'application/json',
      });
      expect(violations).toEqual([]);
      if (route === 'roster') {
        await page.getByRole('tab', { name: /Goalies/ }).click();
        await page.keyboard.press('ArrowRight');
        await expect(page.getByRole('tab', { name: /Injured \(2\)/ })).toHaveAttribute(
          'aria-selected',
          'true',
        );
        await page.getByRole('button', { name: 'Inspect Demo Forward', exact: true }).click();
        await page.getByRole('button', { name: 'View Full Player Profile →', exact: true }).click();
        await expect(page.getByRole('heading', { level: 1, name: 'Demo Forward' })).toBeVisible();
        await expect(page.locator('.profile-hero img[data-image-kind="photo"]')).toHaveCount(0);
      }
      if (route.startsWith('profile/')) {
        await page.getByRole('tab', { name: 'Game Log', exact: true }).click();
        await expect(page.getByText('No game-log provider is connected.')).toBeVisible();
        await page.keyboard.press('Home');
        await expect(page.getByRole('tab', { name: 'Season Stats', exact: true })).toHaveAttribute(
          'aria-selected',
          'true',
        );
      }
      expect(external).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
