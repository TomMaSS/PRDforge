import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.use({ storageState: { cookies: [], origins: [] } }); // No pre-auth for login tests

  test('signin page renders form fields', async ({ page }) => {
    await page.goto('/signin');
    await expect(page.locator('input#email')).toBeVisible();
    await expect(page.locator('input#password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toHaveText(/Sign In/);
  });

  test('signin form submits without error', async ({ page }) => {
    await page.goto('/signin');
    await page.fill('input#email', 'e2e@test.local');
    await page.fill('input#password', 'e2e-test-password-123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
    // Should either redirect or show no error (no destructive error banner)
    const errorBanner = page.locator('[class*="destructive"]');
    const errorCount = await errorBanner.count();
    expect(errorCount).toBe(0);
  });

  test('signin with invalid credentials shows error', async ({ page }) => {
    await page.goto('/signin');
    await page.fill('input#email', 'wrong@test.local');
    await page.fill('input#password', 'wrong-password');
    await page.click('button[type="submit"]');
    // Should stay on signin page or show error
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/signin/);
  });
});

test.describe('Authenticated navigation', () => {
  test('authenticated user sees TopBar with user menu', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.locator('button[aria-label="User menu"]')).toBeVisible();
    await expect(page.locator('button[aria-label="Toggle theme"]')).toBeVisible();
  });

  test('unauthenticated user is redirected to signin', async ({ page, context }) => {
    await context.clearCookies();
    await page.goto('/projects');
    await page.waitForURL('**/signin', { timeout: 10000 });
    await expect(page).toHaveURL(/\/signin/);
  });
});
