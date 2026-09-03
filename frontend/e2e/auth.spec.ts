import { expect, test } from '@playwright/test';

/**
 * Auth UI E2E - verifies the Google Material Design login/register flows.
 * Runs against both local preview (E2E_BASE_URL unset) and production
 * (E2E_BASE_URL=https://smart-doc-chatbot.pages.dev).
 *
 * The actual API auth contract (csrf -> register -> login) is covered by the
 * dedicated fullstack-smoke.spec.ts, which performs the full CSRF handshake.
 */

test.describe('Auth Flow', () => {
  test('unauthenticated visitor is presented with login', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Smart Document', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Chào mừng trở lại').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Tiếp tục', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: /Tiếp tục với Google/i })).toBeVisible();
  });

  test('visitor can switch to register mode and see password fields', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
    await expect(page.getByText('Bắt đầu với Smart Doc miễn phí').first()).toBeVisible();
    await expect(page.getByText('Email hoặc tên đăng nhập').first()).toBeVisible();
    await expect(page.getByText('Mật khẩu').first()).toBeVisible();
    await expect(page.getByText('Xác nhận mật khẩu').first()).toBeVisible();
  });

  test('login form validates empty fields', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('button', { name: 'Tiếp tục', exact: true }).click();
    await expect(page.getByText('Vui lòng điền đầy đủ thông tin')).toBeVisible();
  });

  test('shows error message on invalid credentials', async ({ page }) => {
    await page.goto('/');

    await page.getByPlaceholder('Email hoặc tên đăng nhập').fill('nonexistent-user');
    await page.getByPlaceholder('Mật khẩu').fill('wrongpassword123!');
    await page.getByRole('button', { name: 'Tiếp tục', exact: true }).click();

    // Error toast appears; wait for any error text in the form area.
    await expect(page.locator('div:has-text("thất bại"), div:has-text("lỗi"), div:has-text("error"), div:has-text("failed"), div:has-text("invalid"), div:has-text("sai"), div:has-text("không")').first()).toBeVisible({ timeout: 10000 });
  });

  test('can navigate to forgot password flow', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('button', { name: 'Quên mật khẩu?' }).click();
    await expect(page.getByText('Đặt lại mật khẩu').first()).toBeVisible();
    await expect(page.locator('input').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Gửi liên kết' })).toBeVisible();
  });
});