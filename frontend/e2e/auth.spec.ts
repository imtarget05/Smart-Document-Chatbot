import { expect, test } from '@playwright/test';

const BACKEND = 'https://smart-doc-backend.onrender.com/api';

test.describe('Auth Flow', () => {
  test('unauthenticated visitor is presented with login', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Smart Document', { exact: false }).first()).toBeVisible();
    await expect(page.locator('h1, h2').getByText(/Ch.*o m.*ng/i).first()).toBeVisible();
    await expect(page.locator('button').filter({ hasText: /Tip.*t/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Google/i })).toBeVisible();
  });

  test('visitor can switch to register mode and see password fields', async ({ page }) => {
    await page.goto('/');

    await page.locator('button').filter({ hasText: /Ta . tai khoan/i }).click();
    await expect(page.locator('h1, h2').getByText(/Bat.*u/i).first()).toBeVisible();
    await expect(page.locator('label').filter({ hasText: /Email/i })).toBeVisible();
    await expect(page.locator('label').filter({ hasText: /Mat kha/i })).toBeVisible();
    await expect(page.locator('label').filter({ hasText: /Xac nhan/i })).toBeVisible();
  });

  test('login form validates empty fields', async ({ page }) => {
    await page.goto('/');

    await page.locator('button').filter({ hasText: /Tip.*t/i }).click();
    await expect(page.locator('text=/Vui.*ng|please|required/i').first()).toBeVisible();
  });

  test('shows error message on invalid credentials', async ({ page }) => {
    await page.goto('/');

    await page.locator('input[type="text"], input[name="username"], input[placeholder*="Email"], input:not([type])').first().fill('nonexistent-user');
    await page.locator('input[type="password"]').first().fill('wrongpassword123!');
    await page.locator('button').filter({ hasText: /Tip.*t/i }).click();

    // Backend returns "Invalid username or password"; check for error dialog
    await expect(page.locator('text=/that bai|khong dung|khong hop le|qua|failed|invalid/i').first()).toBeVisible();
  });

  test('can navigate to forgot password flow', async ({ page }) => {
    await page.goto('/');

    await page.locator('a, button').filter({ hasText: /Quen.*mat/i }).click();
    await expect(page.locator('h1, h2').getByText(/.*t.*l.*u/i).first()).toBeVisible();
    await expect(page.locator('input[type="text"], input[placeholder*="Email"]')).toBeVisible();
    await expect(page.locator('button').filter({ hasText: /Gui/i })).toBeVisible();
  });
});

test.describe('Auth API Contract', () => {
  test('login returns 401 for invalid credentials', async ({ page }) => {
    const response = await page.request.post(BACKEND + '/auth/login', {
      data: { username: 'nonexistent-user', password: 'wrongpassword123!' },
      headers: { 'Content-Type': 'application/json' },
    });
    expect(response.status()).toBe(401);
  });

  test('register with weak password returns error', async ({ page }) => {
    const response = await page.request.post(BACKEND + '/auth/register', {
      data: { username: 'testuser', password: 'short', email: 'test@test.com' },
      headers: { 'Content-Type': 'application/json' },
    });
    expect([400, 401, 403]).toContain(response.status());
  });

  test('reset-password endpoint exists', async ({ page }) => {
    const response = await page.request.post(BACKEND + '/auth/reset-password', {
      data: { email: 'nonexistent@test.com', newPassword: 'TestPassword123!' },
      headers: { 'Content-Type': 'application/json' },
    });
    // Should return 200 (generic response to prevent user enumeration)
    expect([200, 400]).toContain(response.status());
  });
});