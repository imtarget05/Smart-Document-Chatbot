import { expect, test } from '@playwright/test';

const BACKEND = 'https://smart-doc-backend.onrender.com/api';

test.describe('Admin API Guards', () => {
  test('audit-logs endpoint requires authentication', async ({ page }) => {
    const response = await page.request.get(BACKEND + '/admin/audit-logs');
    expect([401, 403, 404]).toContain(response.status());
  });
});

test.describe('UI Contracts', () => {
  test('login page renders Google Material Design elements', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1, h2').getByText(/Ch.*o m.*ng/i).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Google/i })).toBeVisible();
  });

  test('register mode shows additional field', async ({ page }) => {
    await page.goto('/');
    await page.locator('button').filter({ hasText: /Ta . tai khoan/i }).click();
    await expect(page.locator('label').filter({ hasText: /Xac nhan/i })).toBeVisible();
  });
});