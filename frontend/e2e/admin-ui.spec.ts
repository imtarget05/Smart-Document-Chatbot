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
    await expect(page.getByText('Chào mừng trở lại').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Tiếp tục với Google/i })).toBeVisible();
  });

  test('register mode shows additional confirmation field', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Tạo tài khoản' }).click();
    await expect(page.getByText('Xác nhận mật khẩu')).toBeVisible();
  });
});