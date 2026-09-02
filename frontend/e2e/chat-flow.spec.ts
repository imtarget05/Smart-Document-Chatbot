import { expect, test } from '@playwright/test';

// Chat E2E — tests chat UI flows and API contracts

const BACKEND = 'https://smart-doc-backend.onrender.com/api';

test.describe('Chat UI', () => {
  test('login page renders with floating labels', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1, h2').getByText(/Ch.*o m.*ng/i).first()).toBeVisible();
    // Floating label inputs
    await expect(page.locator('label').filter({ hasText: /Email/i })).toBeVisible();
    await expect(page.locator('label').filter({ hasText: /Mat kha/i })).toBeVisible();
  });

  test('unauthenticated user sees login not chat', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1, h2').getByText(/Ch.*o m.*ng/i).first()).toBeVisible();
    // If authenticated, we'd see ChatPage — instead we see login
  });
});

test.describe('Chat API Contract', () => {
  test('chat endpoints require authentication', async ({ page }) => {
    const endpoints = ['/chat/ask', '/chat/sessions'];
    for (const endpoint of endpoints) {
      const response = await page.request.post(BACKEND + endpoint, {
        data: { question: 'test', sessionId: 'test' },
        headers: { 'Content-Type': 'application/json' },
      });
      // 401 (auth required), 403 (forbidden), or 404 (route not mapped)
      expect([401, 403, 404]).toContain(response.status());
    }
  });

  test('chat history endpoint requires authentication', async ({ page }) => {
    const response = await page.request.get(BACKEND + '/chat/history/test-session');
    expect([401, 403, 404]).toContain(response.status());
  });

  test('chat delete endpoint requires authentication', async ({ page }) => {
    const response = await page.request.delete(BACKEND + '/chat/history/test-session');
    expect([401, 403, 404]).toContain(response.status());
  });
});