import { expect, test } from '@playwright/test';

// Documents E2E — requires a registered+authenticated user or checks auth-gated responses
// These tests verify the UI document management flows.

test.describe('Document Management UI', () => {
  test('unauthenticated user cannot access documents API', async ({ page }) => {
    // Directly hitting the API without auth → expect 401/403
    const response = await page.request.get('https://smart-doc-backend.onrender.com/api/documents');
    expect([401, 403]).toContain(response.status());
  });

  test('documents page shows upload area when logged in', async ({ page }) => {
    // UI test: navigate to app, login flow, then check document upload UI
    test.skip('Requires authenticated session — covered by auth flow');
  });

  test('upload area accepts valid file types', async ({ page }) => {
    test.skip('Requires authenticated session');
    // Would test: .pdf, .txt, .docx drag-drop acceptance
  });

  test('upload area rejects unsupported file types', async ({ page }) => {
    test.skip('Requires authenticated session');
  });
});