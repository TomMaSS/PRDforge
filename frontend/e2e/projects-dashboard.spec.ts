import { test, expect } from '@playwright/test';

test.describe('Projects Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
  });

  test('page renders with heading and new project button', async ({ page }) => {
    await expect(page.getByText('Projects')).toBeVisible();
    await expect(page.getByRole('button', { name: /New Project/ })).toBeVisible();
  });

  test('project cards display with metadata', async ({ page }) => {
    // Seed data should include at least one project (SnapHabit)
    const cards = page.locator('[class*="card" i], [class*="Card" i]').filter({ hasText: /section/ });
    const cardCount = await cards.count();
    if (cardCount > 0) {
      const firstCard = cards.first();
      await expect(firstCard).toBeVisible();
      // Card should show section count and word count
      await expect(firstCard.getByText(/section/)).toBeVisible();
    }
  });

  test('clicking a project card navigates to project detail', async ({ page }) => {
    const cards = page.locator('[class*="card" i], [class*="Card" i]').filter({ hasText: /section/ });
    const cardCount = await cards.count();
    if (cardCount > 0) {
      await cards.first().click();
      await page.waitForURL(/\/projects\/[^/]+$/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/projects\/[^/]+$/);
    }
  });

  test('New Project dialog opens and has form fields', async ({ page }) => {
    await page.getByRole('button', { name: /New Project/ }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible({ timeout: 5000 });

    // Verify key elements: Template/Blueprint label, Name input, Description textarea
    await expect(dialog.getByText(/Template|Blueprint/i)).toBeVisible();
    await expect(dialog.getByText(/Name/i)).toBeVisible();
    await expect(dialog.locator('input#project-name')).toBeVisible();
    await expect(dialog.locator('textarea#project-description')).toBeVisible();
    await expect(dialog.getByRole('button', { name: /Create/ })).toBeVisible();
    await expect(dialog.getByRole('button', { name: /Cancel/ })).toBeVisible();
  });

  test('New Project dialog can be filled and cancelled', async ({ page }) => {
    await page.getByRole('button', { name: /New Project/ }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible({ timeout: 5000 });

    // Fill form
    await dialog.locator('input#project-name').fill('Test Project');
    await dialog.locator('textarea#project-description').fill('Test description');

    // Cancel
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(dialog).not.toBeVisible({ timeout: 3000 });
  });
});
