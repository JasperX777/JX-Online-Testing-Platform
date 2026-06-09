import { expect, test } from '@playwright/test'

test('user signs in, reviews analytics, and creates a schedule', async ({ page }) => {
  const schedules = []
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()

    if (path === '/api/auth/token/') return route.fulfill({ json: { access: 'access', refresh: 'refresh' } })
    if (path === '/api/auth/me/') return route.fulfill({ json: { id: 1, username: 'Jasper', role: 'user' } })
    if (path === '/api/projects/') return route.fulfill({ json: [{ id: 1, name: 'Login Project' }] })
    if (path === '/api/testcases/') return route.fulfill({ json: [{ id: 2, project: 1, title: 'Valid login' }] })
    if (path === '/api/executions/') return route.fulfill({ json: [] })
    if (path === '/api/executions/analytics/') {
      return route.fulfill({
        json: {
          pass_rate: 80,
          trend: Array.from({ length: 7 }, (_, index) => ({
            date: `2026-06-${String(index + 1).padStart(2, '0')}`,
            total: index,
            success: index,
            failed: 0,
          })),
        },
      })
    }
    if (path === '/api/execution-schedules/' && method === 'POST') {
      schedules.push({
        id: 9,
        project_name: 'Login Project',
        testcase_title: 'Valid login',
        scheduled_for: JSON.parse(route.request().postData()).scheduled_for,
        status: 'pending',
      })
      return route.fulfill({ status: 201, json: schedules[0] })
    }
    if (path === '/api/execution-schedules/') return route.fulfill({ json: schedules })
    return route.fulfill({ json: [] })
  })

  await page.goto('/login')
  await page.getByLabel('Username').fill('Jasper')
  await page.getByLabel('Password').fill('secret')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()

  await expect(page.getByText('Completed pass rate: 80%')).toBeVisible()
  await page.getByRole('link', { name: 'Executions' }).click()
  await page.getByRole('combobox').nth(0).selectOption('1')
  await page.getByRole('combobox').nth(1).selectOption('2')
  await page.getByLabel('Scheduled execution time').fill('2026-06-12T10:30')
  await page.getByRole('button', { name: 'Schedule' }).click()

  await expect(page.getByText('Execution scheduled.')).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Valid login' })).toBeVisible()
})
