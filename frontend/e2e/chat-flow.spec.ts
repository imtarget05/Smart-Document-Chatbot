import { expect, test } from '@playwright/test';

// Chat E2E - UI flows + API contract checks.
// API checks use fetch with redirect:'manual' to report real 3xx/401/403.
const BACKEND = process.env.E2E_API_URL || 'https://smart-doc-backend-h4mt.onrender.com/api';

test.describe('Chat UI', () => {
  test('login page renders with floating labels', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Chào mừng trở lại').first()).toBeVisible();
    await expect(page.getByText('Email hoặc tên đăng nhập').first()).toBeVisible();
    await expect(page.getByText('Mật khẩu').first()).toBeVisible();
  });

  test('unauthenticated user sees login not chat', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Chào mừng trở lại').first()).toBeVisible();
  });
});

test.describe('Chat API Contract', () => {
  test('chat endpoints require authentication', async () => {
    const forEndpoint = async (ep: string) =>
      fetch(BACKEND + ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: 'test', sessionId: 'test' }),
        redirect: 'manual',
      });
    for (const ep of ['/chat/ask', '/chat/sessions']) {
      const res = await forEndpoint(ep);
      expect([302, 303, 307, 401, 403, 404]).toContain(res.status);
    }
  });

  test('chat history endpoint requires authentication', async () => {
    const res = await fetch(BACKEND + '/chat/history/test-session', { redirect: 'manual' });
    expect([302, 303, 307, 401, 403, 404]).toContain(res.status);
  });

  test('chat delete endpoint requires authentication', async () => {
    const res = await fetch(BACKEND + '/chat/history/test-session', {
      method: 'DELETE',
      redirect: 'manual',
    });
    expect([302, 303, 307, 401, 403, 404]).toContain(res.status);
  });
});