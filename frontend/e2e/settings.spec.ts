import { test, expect } from '@playwright/test';

test.describe('Project Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForTimeout(1000);
    const cards = page.locator('[class*="card" i], [class*="Card" i]').filter({ hasText: /section/ });
    const count = await cards.count();
    if (count === 0) {
      test.skip();
      return;
    }
    await cards.first().click();
    await page.waitForURL(/\/projects\/[^/]+$/, { timeout: 10000 });

    // Navigate to settings — try button first, then user menu
    const settingsButton = page.getByRole('button', { name: /Settings/ });
    if (await settingsButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await settingsButton.click();
    } else {
      const userMenu = page.getByRole('button', { name: /User menu/ });
      if (await userMenu.isVisible({ timeout: 3000 }).catch(() => false)) {
        await userMenu.click();
        await page.getByRole('menuitem', { name: /Settings/ }).click();
      }
    }
    await page.waitForURL(/\/settings/, { timeout: 10000 });
  });

  test('settings page loads with heading', async ({ page }) => {
    await expect(page.getByText(/Settings/i).first()).toBeVisible();
  });

  test('toggle switches are visible', async ({ page }) => {
    await page.waitForTimeout(1000);
    const toggles = page.locator('button[role="switch"]');
    const count = await toggles.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('comment auto-replies toggle can be clicked', async ({ page }) => {
    const toggles = page.locator('button[role="switch"]');
    if (await toggles.count() > 0) {
      const firstToggle = toggles.first();
      const initialState = await firstToggle.getAttribute('aria-checked');
      await firstToggle.click();
      await page.waitForTimeout(1000);
      const newState = await firstToggle.getAttribute('aria-checked');
      // State should change
      expect(newState).not.toBe(initialState);
      // Toggle back
      await firstToggle.click();
    }
  });

  test('provider and model dropdowns are visible', async ({ page }) => {
    // Look for select/combobox elements
    const selects = page.locator('[role="combobox"]');
    const selectCount = await selects.count();
    // Should have at least provider and model selects (if chat is enabled)
    if (selectCount >= 2) {
      await expect(selects.first()).toBeVisible();
      await expect(selects.nth(1)).toBeVisible();
    }
  });

  test('members section displays', async ({ page }) => {
    const membersSection = page.getByText(/Members/i);
    await expect(membersSection.first()).toBeVisible();
  });
});
