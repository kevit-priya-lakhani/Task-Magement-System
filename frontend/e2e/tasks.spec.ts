/**
 * e2e/tasks.spec.ts — End-to-End tests for the Task Management System
 *
 * Scenarios covered:
 *   1. Page load        — app renders, task table is visible, header shows task count
 *   2. Add task         — open modal, fill form, submit, new task appears in list
 *   3. Complete task    — click complete on an in-progress task, status changes to Done
 *   4. Delete task      — click delete on a task, task disappears from list
 *   5. Priority filter  — selecting "High" priority shows only high-priority tasks
 *
 * Prerequisites (must be running before executing tests):
 *   - Backend:  http://127.0.0.1:8000   (FastAPI via uvicorn)
 *   - Frontend: http://localhost:5173   (Vite dev server)
 *
 * Run:
 *   npx playwright test --config=playwright.config.ts
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Navigate to the app and wait for the task table to be visible. */
async function gotoApp(page: Page) {
  await page.goto(BASE_URL);
  await page.waitForSelector('table[aria-label="Task list"]', { state: 'visible', timeout: 10_000 });
}

/** Open the "New Task" modal via the header button. */
async function openAddModal(page: Page) {
  await page.getByRole('button', { name: 'Add new task' }).click();
  await expect(page.getByRole('dialog', { name: 'New Task' })).toBeVisible();
}

/**
 * Create a task through the UI modal.
 * Returns the task title so callers can use it for assertions.
 */
async function createTaskViaUI(
  page: Page,
  opts: { title: string; description?: string; priority?: string; status?: string },
): Promise<string> {
  await openAddModal(page);
  const dialog = page.getByRole('dialog', { name: 'New Task' });

  await dialog.getByRole('textbox', { name: 'Title *' }).fill(opts.title);

  if (opts.description) {
    await dialog.getByRole('textbox', { name: 'Description' }).fill(opts.description);
  }
  if (opts.priority) {
    await dialog.getByLabel('Priority').selectOption(opts.priority);
  }
  if (opts.status) {
    await dialog.getByLabel('Status').selectOption(opts.status);
  }

  await dialog.getByRole('button', { name: 'Create Task' }).click();
  await expect(dialog).not.toBeVisible({ timeout: 5_000 });
  return opts.title;
}

// ---------------------------------------------------------------------------
// 1. Page Load
// ---------------------------------------------------------------------------

test.describe('Page load', () => {
  test('renders the app with header, toolbar and task table', async ({ page }) => {
    await gotoApp(page);

    // Header brand title
    await expect(page.getByText('Task Manager')).toBeVisible();

    // "Add Task" button in header
    await expect(page.getByRole('button', { name: 'Add new task' })).toBeVisible();

    // Toolbar: search input and filter dropdowns
    await expect(page.getByRole('searchbox', { name: 'Search tasks' })).toBeVisible();
    await expect(page.getByLabel('Filter by status')).toBeVisible();
    await expect(page.getByLabel('Filter by priority')).toBeVisible();

    // Task table with expected column headers
    const table = page.getByRole('table', { name: 'Task list' });
    await expect(table).toBeVisible();
    await expect(table.getByRole('columnheader', { name: 'Title' })).toBeVisible();
    await expect(table.getByRole('columnheader', { name: 'Priority' })).toBeVisible();
    await expect(table.getByRole('columnheader', { name: 'Status' })).toBeVisible();
    await expect(table.getByRole('columnheader', { name: 'Created' })).toBeVisible();

    // Task count badge in header is a positive number
    const countBadgeText = await page.locator('.header-meta').textContent();
    const count = parseInt(countBadgeText ?? '0', 10);
    expect(count).toBeGreaterThan(0);

    await page.screenshot({
      path: '../screenshots/01-page-load.png',
      fullPage: true,
    });
  });
});

// ---------------------------------------------------------------------------
// 2. Add Task
// ---------------------------------------------------------------------------

test.describe('Add task', () => {
  test('opens modal, fills form, submits and new task appears in list', async ({ page }) => {
    await gotoApp(page);

    const taskTitle = `PW-Add-${Date.now()}`;

    // Capture count before adding
    const beforeText = await page.locator('.header-meta').textContent();
    const beforeCount = parseInt(beforeText ?? '0', 10);

    // Open modal — screenshot while modal is open
    await openAddModal(page);
    const dialog = page.getByRole('dialog', { name: 'New Task' });
    await dialog.getByRole('textbox', { name: 'Title *' }).fill(taskTitle);
    await dialog.getByRole('textbox', { name: 'Description' }).fill('Created by Playwright E2E test');
    await dialog.getByLabel('Priority').selectOption('high');

    await page.screenshot({
      path: '../screenshots/02-add-task-modal.png',
    });

    // Submit
    await dialog.getByRole('button', { name: 'Create Task' }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5_000 });

    // New task row must appear in the table
    const newRow = page.getByRole('row', { name: new RegExp(taskTitle) });
    await expect(newRow).toBeVisible({ timeout: 5_000 });

    // Count must have increased by 1
    const afterText = await page.locator('.header-meta').textContent();
    const afterCount = parseInt(afterText ?? '0', 10);
    expect(afterCount).toBe(beforeCount + 1);

    await page.screenshot({
      path: '../screenshots/03-task-added.png',
      fullPage: true,
    });

    // Cleanup: delete the task we just created
    await newRow.getByRole('button', { name: new RegExp(`Delete task: ${taskTitle}`) }).click();
    await expect(page.getByRole('row', { name: new RegExp(taskTitle) })).not.toBeVisible({ timeout: 5_000 });
  });
});

// ---------------------------------------------------------------------------
// 3. Complete Task
// ---------------------------------------------------------------------------

test.describe('Complete task', () => {
  test('advances an in-progress task to done when complete button is clicked', async ({ page }) => {
    await gotoApp(page);

    // Create a task in "in-progress" state so we always have one to complete
    const taskTitle = `PW-Complete-${Date.now()}`;
    await createTaskViaUI(page, { title: taskTitle, status: 'in-progress' });

    // Locate the complete button for this specific task
    const taskRow = page.getByRole('row', { name: new RegExp(taskTitle) });
    const completeBtn = taskRow.getByRole('button', { name: new RegExp(`Complete task: ${taskTitle}`) });
    await expect(completeBtn).toBeVisible({ timeout: 5_000 });

    await completeBtn.click();

    // The complete button must disappear (task is now done)
    await expect(completeBtn).not.toBeVisible({ timeout: 5_000 });

    // The row's status badge must show "Done"
    await expect(taskRow.getByText('Done')).toBeVisible({ timeout: 5_000 });

    await page.screenshot({
      path: '../screenshots/04-complete-task.png',
      fullPage: true,
    });

    // Cleanup
    await taskRow.getByRole('button', { name: new RegExp(`Delete task: ${taskTitle}`) }).click();
    await expect(taskRow).not.toBeVisible({ timeout: 5_000 });
  });
});

// ---------------------------------------------------------------------------
// 4. Delete Task
// ---------------------------------------------------------------------------

test.describe('Delete task', () => {
  test('removes a task from the list after clicking delete', async ({ page }) => {
    await gotoApp(page);

    const taskTitle = `PW-Delete-${Date.now()}`;
    await createTaskViaUI(page, { title: taskTitle });

    // Verify task row is present
    const taskRow2 = page.getByRole('row', { name: new RegExp(taskTitle) });
    await expect(taskRow2).toBeVisible({ timeout: 5_000 });

    const beforeText = await page.locator('.header-meta').textContent();
    const beforeCount = parseInt(beforeText ?? '0', 10);

    await taskRow2.getByRole('button', { name: new RegExp(`Delete task: ${taskTitle}`) }).click();

    // Task row must disappear from the table
    await expect(page.getByRole('row', { name: new RegExp(taskTitle) })).not.toBeVisible({ timeout: 5_000 });

    // Count must decrease by 1
    const afterText = await page.locator('.header-meta').textContent();
    const afterCount = parseInt(afterText ?? '0', 10);
    expect(afterCount).toBe(beforeCount - 1);

    await page.screenshot({
      path: '../screenshots/05-delete-task.png',
      fullPage: true,
    });
  });
});

// ---------------------------------------------------------------------------
// 5. Priority Filter
// ---------------------------------------------------------------------------

test.describe('Priority filter', () => {
  test('filters task list to show only high-priority tasks', async ({ page }) => {
    await gotoApp(page);

    // Ensure there is at least one high-priority task to filter on
    const highTitle = `PW-High-${Date.now()}`;
    await createTaskViaUI(page, { title: highTitle, priority: 'high' });

    // Also create a low-priority task so we can verify it is hidden
    const lowTitle = `PW-Low-${Date.now()}`;
    await createTaskViaUI(page, { title: lowTitle, priority: 'low' });

    // Apply High priority filter
    await page.getByLabel('Filter by priority').selectOption('high');

    // High-priority task row must be visible
    await expect(page.getByRole('row', { name: new RegExp(highTitle) })).toBeVisible({ timeout: 5_000 });

    // Low-priority task row must be hidden
    await expect(page.getByRole('row', { name: new RegExp(lowTitle) })).not.toBeVisible({ timeout: 3_000 });

    // All visible priority badges must be "High"
    const priorityBadges = page.locator('.badge-priority-high');
    const count = await priorityBadges.count();
    expect(count).toBeGreaterThan(0);

    await page.screenshot({
      path: '../screenshots/06-priority-filter.png',
      fullPage: true,
    });

    // Cleanup: reset filter and delete test tasks
    await page.getByLabel('Filter by priority').selectOption('');
    await page.getByRole('row', { name: new RegExp(highTitle) })
      .getByRole('button', { name: new RegExp(`Delete task: ${highTitle}`) }).click();
    await expect(page.getByRole('row', { name: new RegExp(highTitle) })).not.toBeVisible({ timeout: 5_000 });

    await page.getByRole('row', { name: new RegExp(lowTitle) })
      .getByRole('button', { name: new RegExp(`Delete task: ${lowTitle}`) }).click();
    await expect(page.getByRole('row', { name: new RegExp(lowTitle) })).not.toBeVisible({ timeout: 5_000 });
  });
});
