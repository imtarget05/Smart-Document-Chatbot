import { expect, test } from '@playwright/test';

// Admin E2E — tests admin endpoint auth guards (require ROLE_ADMIN)

const BACKEND = 'https://smart-doc-backend.onrender.com/api';

test.describe('Admin API Guards', () => {
  test('audit-logs endpoint requires authentication', async ({ page }) => {
    const response = await page.request.get(BACKEND + '/admin/audit-logs');
    // Should be 401 (unauthenticated), 403 (forbidden), or 404 (route not mapped)
    expect([401, 403, 404]).toContain(response.status());
  });

  test('audit-logs returns proper structure with ADMIN token', async ({ page }) => {
    test.skip('Requires admin JWT token — not available in E2E without backend test fixtures');
  });
});

// UI Contract tests — verify all static UI elements render correctly
test.describe('UI Contracts', () => {
  test('login page renders Google Material Design elements', async ({ page }) => {
    await page.goto('/');
    
    // Left panel branding
    await expect(page.getByText('Smart Document', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Chào mừng trở lại').first()).toBeVisible();
    
    // Google OAuth button
    await expect(page.getByRole('button', { name: /Google/ })).toBeVisible();
    
    // Floating label inputs
    await expect(page.getByPlaceholder('Email hoặc tên đăng nhập')).toBeVisible();
    await expect(page.getByPlaceholder('Mật khẩu', { exact: true })).toBeVisible();
  });

  test('register mode shows additional fields', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Tạo tài khoản' }).click();
    
    await expect(page.getByText('Bắt đầu với Smart Doc miễn phí')).toBeVisible();
    await expect(page.getByPlaceholder('Xác nhận mật khẩu')).toBeVisible();
  });
});