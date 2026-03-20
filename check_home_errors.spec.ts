import { test, expect } from '@playwright/test';

test('Check console errors on home page', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  page.on('pageerror', exception => {
    errors.push(exception.message);
  });

  await page.goto('http://127.0.0.1:8000/');

  // Wait a bit to let JS run
  await page.waitForTimeout(2000);

  console.log('--- CONSOLE ERRORS ---');
  console.log(errors);
});
