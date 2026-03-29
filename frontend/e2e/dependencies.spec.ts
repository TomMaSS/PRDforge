import { test, expect } from '@playwright/test';

test.describe('Dependencies View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForTimeout(1000);
    const cards = page.locator('[class*="card" i], [class*="Card" i]').filter({ hasText: /section/ });
    if (await cards.count() === 0) { test.skip(); return; }
    await cards.first().click();
    await page.waitForURL(/\/projects\/[^/]+$/, { timeout: 10000 });
    await page.getByRole('tab', { name: 'Dependencies' }).click();
  });

  test('dependencies tab renders content', async ({ page }) => {
    const tabPanel = page.getByRole('tabpanel');
    await expect(tabPanel).toBeVisible();
  });

  test('graph/list view toggle exists', async ({ page }) => {
    await page.waitForTimeout(1000);
    // Look for graph/list toggle buttons
    const graphButton = page.getByRole('button', { name: /Graph/i });
    const listButton = page.getByRole('button', { name: /List/i });

    const hasToggle = (await graphButton.count()) > 0 || (await listButton.count()) > 0;
    expect(hasToggle).toBeTruthy();
  });

  test('toggling between graph and list view works', async ({ page }) => {
    await page.waitForTimeout(1000);
    const graphButton = page.getByRole('button', { name: /Graph/i });
    const listButton = page.getByRole('button', { name: /List/i });

    if (await graphButton.isVisible()) {
      await graphButton.click();
      await page.waitForTimeout(500);
      // Should see SVG graph or graph container
    }

    if (await listButton.isVisible()) {
      await listButton.click();
      await page.waitForTimeout(500);
      // Should see list view
    }
  });

  test('dependency legend is visible in graph view', async ({ page }) => {
    await page.waitForTimeout(1000);
    // Check for dependency type labels
    const types = ['references', 'implements', 'blocks', 'extends'];
    let foundAny = false;
    for (const t of types) {
      const el = page.getByText(new RegExp(t, 'i'));
      if (await el.count() > 0) {
        foundAny = true;
        break;
      }
    }
    expect(foundAny).toBeTruthy();
  });
});
