import { chromium, type FullConfig } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8088';
const TEST_USER = {
  name: 'E2E Test User',
  email: 'e2e@test.local',
  password: 'e2e-test-password-123',
};

async function globalSetup(_config: FullConfig) {
  // Step 1: Try bootstrap (creates first user + org on fresh DB)
  const setupRes = await fetch(`${BASE_URL}/api/auth/setup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(TEST_USER),
  });

  if (setupRes.status === 200) {
    console.log('Global setup: created first user via /api/auth/setup');
  } else if (setupRes.status === 409) {
    console.log('Global setup: bootstrap already done, ensuring test user exists...');
    const signupRes = await fetch(`${BASE_URL}/api/auth/sign-up/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: TEST_USER.name,
        email: TEST_USER.email,
        password: TEST_USER.password,
      }),
    });
    if (signupRes.ok) {
      console.log('Global setup: created test user via signup');
    } else {
      console.log('Global setup: test user likely already exists');
    }
  } else {
    const body = await setupRes.text();
    throw new Error(`Auth setup failed (${setupRes.status}): ${body}`);
  }

  // Step 2: Sign in via browser to get session cookie
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(`${BASE_URL}/signin`);
  await page.fill('input#email', TEST_USER.email);
  await page.fill('input#password', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/projects', { timeout: 15000 });

  // Step 3: Ensure test user has at least one project
  // Create a test project if none exist (uses the authenticated session)
  const projectsRes = await page.evaluate(async () => {
    const res = await fetch('/api/projects');
    return res.json();
  });

  if (!projectsRes || !Array.isArray(projectsRes) || projectsRes.length === 0) {
    console.log('Global setup: no projects found, creating test project...');
    await page.evaluate(async () => {
      await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'E2E Test Project',
          description: 'Automated test project for E2E testing',
          template: 'saas-mvp',
        }),
      });
    });
    // Wait for project to be created
    await page.waitForTimeout(2000);
    console.log('Global setup: test project created');
  } else {
    console.log(`Global setup: ${projectsRes.length} project(s) already exist`);
  }

  // Step 4: Save authenticated state for all tests
  await context.storageState({ path: './e2e/.auth/user.json' });
  await browser.close();

  console.log('Global setup: complete');
}

export default globalSetup;
