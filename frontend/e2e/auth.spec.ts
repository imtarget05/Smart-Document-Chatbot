import { expect, test } from '@playwright/test';

test('unauthenticated visitor is presented with login and registration', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByText('Smart Doc Chatbot')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
  await page.getByRole('button', { name: 'Create Account' }).click();
  await expect(page.getByRole('button', { name: 'Create Account' })).toBeVisible();
});
