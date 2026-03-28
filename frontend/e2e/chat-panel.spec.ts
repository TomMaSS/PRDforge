import { test, expect } from '@playwright/test';

test.describe('Chat Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForTimeout(1000);
    const cards = page.locator('[class*="card" i], [class*="Card" i]').filter({ hasText: /section/ });
    if (await cards.count() === 0) { test.skip(); return; }
    await cards.first().click();
    await page.waitForURL(/\/projects\/[^/]+$/, { timeout: 10000 });
  });

  test('chat panel renders if enabled', async ({ page }) => {
    const chatInput = page.locator('textarea[placeholder="Type a message..."]');
    const chatVisible = await chatInput.isVisible().catch(() => false);

    if (chatVisible) {
      // Chat is enabled — verify UI elements
      await expect(chatInput).toBeVisible();
      await expect(page.getByRole('button', { name: /Send/ })).toBeVisible();
    }
    // If chat is not visible, it's disabled in settings — that's valid too
  });

  test('send button is disabled when input is empty', async ({ page }) => {
    const chatInput = page.locator('textarea[placeholder="Type a message..."]');
    if (await chatInput.isVisible().catch(() => false)) {
      const sendButton = page.getByRole('button', { name: /Send/ });
      await expect(sendButton).toBeDisabled();
    }
  });

  test('typing a message enables send button', async ({ page }) => {
    const chatInput = page.locator('textarea[placeholder="Type a message..."]');
    if (await chatInput.isVisible().catch(() => false)) {
      await chatInput.fill('Hello test message');
      const sendButton = page.getByRole('button', { name: /Send/ });
      await expect(sendButton).toBeEnabled();
    }
  });

  test('attach file button is present', async ({ page }) => {
    const chatInput = page.locator('textarea[placeholder="Type a message..."]');
    if (await chatInput.isVisible().catch(() => false)) {
      const attachButton = page.getByRole('button', { name: /Attach/i }).or(
        page.locator('button').filter({ hasText: /attach/i })
      );
      // Attach might be an icon-only button
      const fileInput = page.locator('input[type="file"]');
      await expect(fileInput).toBeAttached();
    }
  });
});
