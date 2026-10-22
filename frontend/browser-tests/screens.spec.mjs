import { browserOrigin } from '../scripts/browser-server.mjs';
import { test, expect } from 'playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import os from 'node:os';
const require = createRequire(import.meta.url);
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');
test.beforeAll(async ({ browser }) => {
  await mkdir('output/visual', { recursive: true });
  await mkdir('output/playwright/screens', { recursive: true });
  await writeFile(
    'output/playwright/environment.json',
    JSON.stringify(
      {
        platform: process.platform,
        osRelease: os.release(),
        runnerImage: process.env.ImageVersion ?? 'local/unrecorded',
        node: process.version,
        browser: browser.version(),
        playwright: require('playwright/package.json').version,
        fonts: {
          barlow: require('@fontsource/barlow/package.json').version,
          condensed: require('@fontsource/barlow-condensed/package.json').version,
        },
      },
      null,
      2,
    ),
  );
});
const routes = (
  process.env.SCREEN_ROUTES ||
  'overview,roster,profile/matthews,planner,comparison,league,connections,settings'
).split(',');
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
        if (new URL(r.request().url()).origin === browserOrigin) return r.continue();
        external.push(r.request().url());
        return r.abort();
      });
      await page.route('**/axe-check.js', (r) =>
        r.fulfill({ contentType: 'application/javascript', body: axe }),
      );
      await page.setViewportSize({ width, height });
      await page.goto(`/#${route}`);
      if (process.env.LOCAL_API === '1')
        await page.locator('.screen-content[data-source="demo"]').waitFor();
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
        path: `output/playwright/screens/${imageName}`,
        fullPage: true,
        animations: 'disabled',
      });
      if (['1', 'advisory'].includes(process.env.VISUAL_COMPARE)) {
        const advisory = process.env.VISUAL_COMPARE === 'advisory';
        const result = { image: imageName, status: 'matched' };
        try {
          await expect(page).toHaveScreenshot(imageName, {
            fullPage: true,
            animations: 'disabled',
            maxDiffPixelRatio: 0.005,
            ...(advisory ? { timeout: 2000 } : {}),
          });
        } catch (error) {
          result.status = 'mismatch';
          result.detail = String(error.message).slice(0, 2000);
          if (!advisory) throw error;
          testInfo.annotations.push({ type: 'visual-advisory', description: imageName });
        } finally {
          await writeFile(`output/visual/${imageName}.json`, JSON.stringify(result));
        }
      }
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
      if (route === 'planner') {
        await page.getByRole('button', { name: 'Select COL @ STL', exact: true }).click();
        await expect(
          page
            .getByRole('complementary', { name: 'Selected matchup' })
            .getByRole('heading', { name: 'COL @ STL' }),
        ).toBeVisible();
        await page.getByRole('button', { name: 'Next week', exact: true }).click();
        await expect(page.getByText('Schedule coverage is unknown for this date.')).toBeVisible();
      }
      if (route === 'comparison') {
        const first = await page.getByRole('combobox', { name: /^First player/ }).inputValue();
        const second = await page.getByRole('combobox', { name: /^Second player/ }).inputValue();
        await page.getByRole('button', { name: 'Swap players', exact: true }).click();
        await expect(page.getByRole('combobox', { name: /^First player/ })).toHaveValue(second);
        await expect(page.getByRole('combobox', { name: /^Second player/ })).toHaveValue(first);
        await page.getByRole('tab', { name: 'Statistics', exact: true }).click();
        await page.keyboard.press('End');
        await expect(page.getByRole('tab', { name: 'History', exact: true })).toHaveAttribute(
          'aria-selected',
          'true',
        );
      }
      if (route === 'league') {
        const table = page.getByRole('table', { name: 'Demo league standings' });
        await table.getByRole('button', { name: 'Sort by team', exact: true }).click();
        await expect(table.getByRole('row').nth(1)).toContainText('Bay Area Blades');
        await page.getByRole('button', { name: 'Next matchup week', exact: true }).click();
        await expect(
          page.getByText('No synthetic matchup scores loaded for Week 15.'),
        ).toBeVisible();
      }
      if (route === 'connections') {
        await expect(page.getByRole('button', { name: /Sync now/ })).toBeDisabled();
        await page.getByRole('button', { name: /Connection guidance/ }).click();
        await expect(page.getByText(/Do not paste credentials or tokens here/)).toBeVisible();
      }
      if (route === 'settings') {
        await page.getByRole('switch', { name: 'Show team logos', exact: true }).click();
        await expect(page.locator('.app-shell')).toHaveClass(/without-team-logos/);
        const nav = page.getByRole('navigation', { name: 'Settings sections' });
        for (const compact of [false, true]) {
          if (compact) {
            await page.getByRole('switch', { name: 'Compact view', exact: true }).click();
            await expect(page.locator('.app-shell')).toHaveClass(/compact-display/);
          }
          if (width > 1050) {
            const navBounds = await nav.boundingBox();
            const cardsBounds = await page.locator('.settings-center-bottom').boundingBox();
            expect(navBounds).not.toBeNull();
            expect(cardsBounds).not.toBeNull();
            expect(cardsBounds.x).toBeGreaterThanOrEqual(navBounds.x + navBounds.width);
          }
          for (const label of ['Notifications', 'Account', 'About']) {
            const section = nav.getByRole('button', { name: new RegExp(`^${label}`) });
            await section.click();
            await expect(section).toHaveAttribute('aria-pressed', 'true');
            await expect(section).toBeFocused();
          }
          await expect(page).toHaveURL(/#settings$/);
        }
      }
      expect(external).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
