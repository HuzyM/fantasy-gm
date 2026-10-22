import { expect } from 'playwright/test';

export async function keyboardButton(page, name) {
  const button = page.getByRole('button', { name, exact: true });
  await button.focus();
  await page.keyboard.press('Enter');
}

export async function navigate(page, width, name) {
  if (width < 900) await keyboardButton(page, 'Open navigation');
  await keyboardButton(page, name);
  // App.navigate transfers focus in requestAnimationFrame, after the route renders.
  await expect(page.getByRole('main')).toBeFocused();
}

export async function openDisclosure(page, name) {
  const button = page.getByRole('button', { name, exact: true });
  await expect(button).toBeVisible();
  if ((await button.getAttribute('aria-expanded')) !== 'true') await keyboardButton(page, name);
  const region = page.getByRole('region', { name, exact: true });
  await expect(region).toBeVisible();
  return region;
}
