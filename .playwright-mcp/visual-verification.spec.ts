/**
 * AutoBan Visual Verification Test
 *
 * This Playwright test script performs visual verification of the AutoBan application.
 * It tests navigation, authentication, project creation, task management, and agent features.
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = 'http://localhost:3002';
const API_URL = 'https://autoban-api.learnai.cz';

// JWT token for test user (test@example.com)
// In production, this should be generated dynamically or use proper auth flow
const TEST_JWT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZDQ1MDcwMi1jN2YwLTQwZDctODViYS0xN2E2OTgwYWNjNWIiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE3NjgzMzg1Mzl9.zRBDQJ_Y-RgFmhOsfIYzOmlmR5120cO-vF5ToWDZjho';

/**
 * Helper function to set up authentication via route interception
 */
async function setupAuth(page: Page) {
  await page.route('**/api/**', async (route) => {
    const headers = {
      ...route.request().headers(),
      'Authorization': `Bearer ${TEST_JWT_TOKEN}`
    };
    await route.continue({ headers });
  });
}

test.describe('AutoBan Visual Verification', () => {

  test.beforeEach(async ({ page }) => {
    // Set up authentication for all tests
    await setupAuth(page);
  });

  test('Step 1: Navigate to landing page', async ({ page }) => {
    await page.goto(BASE_URL);

    // Verify landing page elements
    await expect(page.getByRole('heading', { name: /Welcome to AutoBan/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Sign in with GitHub/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Sign in with Google/i })).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/01-landing-page.png' });
  });

  test('Step 2: Login and access dashboard', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    // Verify dashboard elements
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByText('Total Projects')).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Project' })).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/02-dashboard.png' });
  });

  test('Step 3: Create new project', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    // Click New Project button
    await page.getByRole('button', { name: 'New Project' }).click();

    // Verify dialog appears
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Create New Project' })).toBeVisible();

    // Fill in project details
    await page.getByRole('textbox', { name: 'Project Name' }).fill('Test Project');
    await page.getByRole('textbox', { name: 'Description' }).fill('Created by Playwright test');

    // Take screenshot of dialog
    await page.screenshot({ path: 'screenshots/03-create-project-dialog.png' });

    // Submit form
    await page.getByRole('button', { name: 'Create Project' }).click();

    // Verify redirected to project page
    await expect(page).toHaveURL(/\/projects\//);
    await expect(page.getByRole('heading', { name: 'Test Project' })).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/04-project-created.png' });
  });

  test('Step 4: View Kanban board with tasks', async ({ page }) => {
    // Navigate to existing project with tasks
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    // Click on a project that has tasks
    await page.getByRole('link', { name: /My First Project/i }).click();
    await page.waitForTimeout(1000);

    // Verify Kanban board
    await expect(page.getByRole('tab', { name: 'Board' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'BACKLOG' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'TODO' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'IN PROGRESS' })).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/05-kanban-board.png' });
  });

  test('Step 5: Move task between columns', async ({ page }) => {
    // Navigate to project with tasks
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);
    await page.getByRole('link', { name: /My First Project/i }).click();
    await page.waitForTimeout(1000);

    // Click on a task to open detail dialog
    await page.locator('h4:has-text("Setup CI/CD pipeline")').click();

    // Verify task detail dialog
    await expect(page.getByRole('dialog')).toBeVisible();

    // Take screenshot of task dialog
    await page.screenshot({ path: 'screenshots/06-task-detail.png' });

    // Change status to "In Progress"
    await page.getByRole('button', { name: 'In Progress' }).click();

    // Close dialog
    await page.getByRole('button', { name: 'Close' }).click();

    // Verify task moved
    const inProgressColumn = page.locator('text=IN PROGRESS').locator('..');
    await expect(inProgressColumn.getByText('Setup CI/CD pipeline')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/07-task-moved.png' });
  });

  test('Step 6: Navigate to Agents page', async ({ page }) => {
    await page.goto(`${BASE_URL}/agents`);
    await page.waitForTimeout(1000);

    // Verify agents page
    await expect(page.getByRole('heading', { name: 'Agents' })).toBeVisible();
    await expect(page.getByText('Manage your AI coding agents')).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/08-agents-page.png' });
  });

  test('Step 7: Verify agent spawn button in project', async ({ page }) => {
    // Navigate to project
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);
    await page.getByRole('link', { name: /My First Project/i }).click();
    await page.waitForTimeout(1000);

    // Click on Agents tab
    await page.getByRole('tab', { name: 'Agents' }).click();

    // Verify Add Agent button is visible
    await expect(page.getByRole('button', { name: 'Add Agent' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Project Agents' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Agent Instances' })).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/09-agent-spawn-button.png' });
  });

});

/**
 * Full end-to-end visual verification test
 */
test('Complete visual verification flow', async ({ page }) => {
  await setupAuth(page);

  // Step 1: Landing page
  await page.goto(BASE_URL);
  await expect(page.getByRole('heading', { name: /Welcome to AutoBan/i })).toBeVisible();
  await page.screenshot({ path: 'screenshots/e2e-01-landing.png' });

  // Step 2: Dashboard
  await page.goto(`${BASE_URL}/dashboard`);
  await page.waitForTimeout(2000);
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await page.screenshot({ path: 'screenshots/e2e-02-dashboard.png' });

  // Step 3: Create project
  await page.getByRole('button', { name: 'New Project' }).click();
  await page.getByRole('textbox', { name: 'Project Name' }).fill('E2E Test Project');
  await page.screenshot({ path: 'screenshots/e2e-03-create-project.png' });
  await page.getByRole('button', { name: 'Create Project' }).click();
  await page.waitForTimeout(1000);

  // Step 4: Navigate to existing project with tasks
  await page.goto(`${BASE_URL}/dashboard`);
  await page.waitForTimeout(2000);
  await page.getByRole('link', { name: /My First Project/i }).click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'screenshots/e2e-04-kanban.png' });

  // Step 5: Open task and change status
  await page.locator('h4').filter({ hasText: /Implement login page|Setup CI\/CD|Add user/i }).first().click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'screenshots/e2e-05-task-detail.png' });
  await page.getByRole('button', { name: 'Close' }).click();

  // Step 6: Navigate to Agents tab
  await page.getByRole('tab', { name: 'Agents' }).click();
  await expect(page.getByRole('button', { name: 'Add Agent' })).toBeVisible();
  await page.screenshot({ path: 'screenshots/e2e-06-agents.png' });

  console.log('Visual verification complete!');
});
