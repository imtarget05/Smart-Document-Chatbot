import { expect, test } from '@playwright/test';

// Admin E2E - auth-gated API check + UI contract tests.
// API check uses fetch with redirect:'manual' to capture the real 3xx/401/403.
const BACKEND = process.env.E2E_API_URL || 'https://smart-doc-backend-h4mt.onrender.com/api';

test.describe('Admin API Guards', () => {
  test('audit-logs endpoint requires authentication', async () => {
    const res = await fetch(BACKEND + '/admin/audit-logs', { redirect: 'manual' });
    expect([302, 303, 307, 401, 403, 404]).toContain(res.status);
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