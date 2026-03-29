import { test, expect } from '@playwright/test';

test.describe('Theme Toggle', () => {
  test('theme toggle button exists on projects page', async ({ page }) => {
    await page.goto('/projects');
    const themeButton = page.locator('button[aria-label="Toggle theme"]');
    await expect(themeButton).toBeVisible();
  });

  test('clicking theme toggle changes body class', async ({ page }) => {
    await page.goto('/projects');
    const themeButton = page.locator('button[aria-label="Toggle theme"]');

    // Get initial theme state
    const initialDark = await page.locator('html').evaluate(el => el.classList.contains('dark'));

    // Toggle theme
    await themeButton.click();
    await page.waitForTimeout(500);

    // Verify class changed
    const afterToggle = await page.locator('html').evaluate(el => el.classList.contains('dark'));
    expect(afterToggle).not.toBe(initialDark);

    // Toggle back to restore original state
    await themeButton.click();
    await page.waitForTimeout(500);

    const restored = await page.locator('html').evaluate(el => el.classList.contains('dark'));
    expect(restored).toBe(initialDark);
  });

  test('theme persists across navigation', async ({ page }) => {
    await page.goto('/projects');
    const themeButton = page.locator('button[aria-label="Toggle theme"]');

    // Set to dark mode
    const isDark = await page.locator('html').evaluate(el => el.classList.contains('dark'));
    if (!isDark) {
      await themeButton.click();
      await page.waitForTimeout(500);
    }

    // Navigate to a different page and back
    await page.goto('/projects');
    await page.waitForTimeout(1000);

    // Should still be dark
    const stillDark = await page.locator('html').evaluate(el => el.classList.contains('dark'));
    expect(stillDark).toBe(true);
  });
});
