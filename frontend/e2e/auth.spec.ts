import { expect, test } from '@playwright/test';

test('unauthenticated visitor is presented with login', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByText('Smart Document', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('Chào mừng trở lại').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Tiếp tục', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Tiếp tục với Google/ })).toBeVisible();
});

test('visitor can switch to register mode and see password fields', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: 'Tạo tài khoản' }).click();
  await expect(page.getByText('Bắt đầu với Smart Doc miễn phí')).toBeVisible();
  await expect(page.getByPlaceholder('Email hoặc tên đăng nhập')).toBeVisible();
  await expect(page.getByPlaceholder('Mật khẩu', { exact: true })).toBeVisible();
  await expect(page.getByPlaceholder('Xác nhận mật khẩu')).toBeVisible();
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

  // Either auth failure or network error — but a visible error state appears
  await expect(page.locator('text=/thất bại|không đúng|không hợp lệ|quá|failed/i').first()).toBeVisible();
});

test('can navigate to forgot password flow', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: 'Quên mật khẩu?' }).click();
  await expect(page.getByText('Đặt lại mật khẩu').first()).toBeVisible();
  await expect(page.getByPlaceholder('Email')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Gửi liên kết' })).toBeVisible();
});
