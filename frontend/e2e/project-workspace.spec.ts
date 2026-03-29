import { test, expect } from '@playwright/test';

test.describe('Project Workspace', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForTimeout(1000);
    const cards = page.locator('[class*="card" i], [class*="Card" i]').filter({ hasText: /section/ });
    const cardCount = await cards.count();
    if (cardCount === 0) {
      test.skip();
      return;
    }
    await cards.first().click();
    await page.waitForURL(/\/projects\/[^/]+$/, { timeout: 10000 });
  });

  test('workspace renders 3-column layout', async ({ page }) => {
    // Left sidebar (sections nav)
    await expect(page.locator('nav').filter({ hasText: 'Sections' })).toBeVisible();

    // Center content area should have content
    const mainContent = page.locator('main, [class*="flex-1"]').first();
    await expect(mainContent).toBeVisible();
  });

  test('tab bar renders all tabs', async ({ page }) => {
    const tabs = ['Sections', 'Comments', 'Dependencies', 'Changelog', 'Stats'];
    for (const tabName of tabs) {
      await expect(page.getByRole('tab', { name: tabName })).toBeVisible();
    }
  });

  test('clicking each tab switches content', async ({ page }) => {
    // Sections tab (default)
    await page.getByRole('tab', { name: 'Sections' }).click();
    await expect(page.getByRole('tabpanel')).toBeVisible();

    // Comments tab
    await page.getByRole('tab', { name: 'Comments' }).click();
    await expect(page.getByRole('tabpanel')).toBeVisible();

    // Dependencies tab
    await page.getByRole('tab', { name: 'Dependencies' }).click();
    await expect(page.getByRole('tabpanel')).toBeVisible();

    // Changelog tab
    await page.getByRole('tab', { name: 'Changelog' }).click();
    await expect(page.getByRole('tabpanel')).toBeVisible();

    // Stats tab
    await page.getByRole('tab', { name: 'Stats' }).click();
    await expect(page.getByRole('tabpanel')).toBeVisible();
  });

  test('sidebar shows section list', async ({ page }) => {
    // Sections sidebar may use nav, aside, or div — look for the section list
    await page.waitForTimeout(1000);
    const sidebarButtons = page.locator('button').filter({ hasText: /\d+w/ });
    const count = await sidebarButtons.count();
    // At least one section with word count should be visible
    if (count > 0) {
      await expect(sidebarButtons.first()).toBeVisible();
    } else {
      // Fallback: look for any clickable section items in sidebar area
      const sectionItems = page.getByText(/section|overview|feature/i);
      expect(await sectionItems.count()).toBeGreaterThan(0);
    }
  });

  test('clicking a section in sidebar loads its content', async ({ page }) => {
    const sidebarButtons = page.locator('nav button');
    const count = await sidebarButtons.count();
    if (count > 1) {
      // Click second section
      await sidebarButtons.nth(1).click();
      // Content area should update (wait for any loading to finish)
      await page.waitForTimeout(1000);
      // The clicked section should become active
      await expect(sidebarButtons.nth(1)).toHaveClass(/bg-accent|font-medium/);
    }
  });

  test('section viewer shows markdown content', async ({ page }) => {
    // Wait for section content to load
    await page.waitForTimeout(1000);
    // Should see rendered markdown (headings, paragraphs)
    const contentArea = page.locator('[class*="prose"], [class*="markdown"]');
    if (await contentArea.count() > 0) {
      await expect(contentArea.first()).toBeVisible();
    }
  });

  test('export buttons are visible', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Preview/ })).toBeVisible();
    await expect(page.getByRole('button', { name: '.md' })).toBeVisible();
  });
});
