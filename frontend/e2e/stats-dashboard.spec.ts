import { test, expect } from '@playwright/test';

test.describe('Stats Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForTimeout(1000);
    const cards = page.locator('[class*="card" i], [class*="Card" i]').filter({ hasText: /section/ });
    if (await cards.count() === 0) { test.skip(); return; }
    await cards.first().click();
    await page.waitForURL(/\/projects\/[^/]+$/, { timeout: 10000 });
    await page.getByRole('tab', { name: 'Stats' }).click();
  });

  test('stats tab renders metric cards', async ({ page }) => {
    // Wait for stats to load
    await page.waitForTimeout(2000);
    const tabPanel = page.getByRole('tabpanel');
    await expect(tabPanel).toBeVisible();

    // Should show some metric-related content (cards, charts, or empty state)
    const hasContent = await tabPanel.locator('text=/token|savings|section|operation/i').count();
    expect(hasContent).toBeGreaterThan(0);
  });

  test('stats tab shows charts or empty state', async ({ page }) => {
    await page.waitForTimeout(2000);
    // Look for recharts SVG elements or empty state messages
    const charts = page.locator('svg.recharts-surface, [class*="recharts"]');
    const emptyState = page.getByText(/no data|no usage|no activity/i);

    const chartCount = await charts.count();
    const emptyCount = await emptyState.count();

    // Either charts render OR empty state shows — both are valid
    expect(chartCount + emptyCount).toBeGreaterThan(0);
  });
});
