import { defineConfig, devices } from '@playwright/test';

// Allow E2E testing against production by setting E2E_BASE_URL:
//   E2E_BASE_URL=https://smart-doc-chatbot.pages.dev npx playwright test
// When E2E_BASE_URL is set, no local webServer is started.
const useProduction = !!process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: './e2e',
  // Staging-facing suites race Render redeploys/cold starts; one retry keeps
  // transient 502s from failing the gate.
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: useProduction ? process.env.E2E_BASE_URL : 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
    ...devices['Desktop Chrome'],
    // Longer timeouts for production/staging cold starts
    actionTimeout: useProduction ? 15000 : 10000,
    navigationTimeout: useProduction ? 30000 : 10000,
  },
  // Only start the preview server when not targeting production
  ...(useProduction
    ? {}
    : {
        webServer: {
          command: 'npm run build && npm run preview -- --host 127.0.0.1',
          port: 4173,
          reuseExistingServer: !process.env.CI,
        },
      }),
});
