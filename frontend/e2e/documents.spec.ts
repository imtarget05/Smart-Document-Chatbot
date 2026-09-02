import { expect, test } from '@playwright/test';

// Documents E2E - auth-gated API checks against the live backend.
// Uses global fetch with redirect:'manual' so an unauthenticated hit reports
// its real 3xx/401/403 status instead of silently following to the login page.
const BACKEND = process.env.E2E_API_URL || 'https://smart-doc-backend-h4mt.onrender.com/api';

test.describe('Document Management API Guards', () => {
  test('unauthenticated user is not granted documents data', async () => {
    const res = await fetch(BACKEND + '/documents', { redirect: 'manual' });
    // Protected: redirects to login (302/303) or returns 401/403/404.
    expect([302, 303, 307, 401, 403, 404]).toContain(res.status);
  });

  test('document upload requires authentication', async () => {
    const fd = new FormData();
    fd.append('file', new Blob(['hello']), 'upload.txt');
    const res = await fetch(BACKEND + '/documents/upload', {
      method: 'POST',
      body: fd,
      redirect: 'manual',
    });
    expect([302, 303, 307, 401, 403, 404]).toContain(res.status);
  });
});