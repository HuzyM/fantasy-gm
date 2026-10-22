import { expect } from 'playwright/test';

// Hold only the replacement session's fabricated response until loading is visible.
export async function replaceSession(page, capability, view) {
  let release;
  const captured = new Promise((resolve) => {
    release = resolve;
  });
  let held = false;
  const handler = (route) => {
    if (!held && route.request().headers().authorization === `Bearer ${capability}`) {
      held = true;
      release(route);
    } else return route.fallback();
  };
  await page.route('**/api/view', handler);
  try {
    await page.goto(`/#access=${capability}`);
    const route = await captured;
    await expect(page.getByRole('heading', { name: 'Loading local session' })).toBeVisible();
    await route.fulfill({ json: view });
    await expect(page.locator('.screen-content')).toHaveAttribute('data-source', 'private');
  } finally {
    await page.unroute('**/api/view', handler);
  }
}
