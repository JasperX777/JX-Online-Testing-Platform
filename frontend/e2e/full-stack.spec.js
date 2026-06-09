import { expect, test } from '@playwright/test'

test('real stack creates, schedules, executes, and reviews a browser test', async ({ page, request }) => {
  const suffix = Date.now()
  const username = `full_stack_${suffix}`
  const password = 'FullStackPass123!'

  const registerResponse = await request.post('/api/auth/register/', {
    data: { username, email: `${username}@example.com`, password },
  })
  expect(registerResponse.status()).toBe(201)

  const tokenResponse = await request.post('/api/auth/token/', {
    data: { username, password },
  })
  expect(tokenResponse.status()).toBe(200)
  const { access } = await tokenResponse.json()
  const headers = { Authorization: `Bearer ${access}` }

  const projectResponse = await request.post('/api/projects/', {
    headers,
    data: { name: `Full Stack ${suffix}`, description: 'Real integration test project' },
  })
  expect(projectResponse.status()).toBe(201)
  const project = await projectResponse.json()

  const testcaseResponse = await request.post('/api/testcases/', {
    headers,
    data: {
      project: project.id,
      title: 'Open backend health endpoint',
      module: 'Integration',
      scenario: 'Backend health',
      category: 'full-stack',
      tags: ['integration'],
      priority: 'high',
      status: 'ready',
      steps_json: [
        {
          step_no: 1,
          step_title: 'Launch Chromium',
          description: 'Launch the Chromium browser.',
          action: 'launch_browser',
          target: '',
          locator_type: 'css',
          selector: '',
          value: 'chromium',
          note: '',
        },
        {
          step_no: 2,
          step_title: 'Open backend health endpoint',
          description: 'Open the real backend health endpoint.',
          action: 'open_page',
          target: 'Backend health endpoint',
          locator_type: 'css',
          selector: '',
          value: 'http://127.0.0.1:8000/api/health/',
          note: '',
        },
      ],
    },
  })
  expect(testcaseResponse.status()).toBe(201)
  const testcase = await testcaseResponse.json()

  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

  await page.getByRole('link', { name: 'Executions' }).click()
  await page.getByRole('combobox').nth(0).selectOption(String(project.id))
  await page.getByRole('combobox').nth(1).selectOption(String(testcase.id))
  await page.getByLabel('Scheduled execution time').fill('2027-06-12T10:30')
  await page.getByRole('button', { name: 'Schedule' }).click()
  await expect(page.getByText('Execution scheduled.')).toBeVisible()

  const runResponse = await request.post('/api/executions/run/', {
    headers,
    data: { project: project.id, testcase: testcase.id },
  })
  expect(runResponse.status()).toBe(201)
  const execution = await runResponse.json()

  const detailResponse = await request.get(`/api/executions/${execution.id}/`, { headers })
  expect(detailResponse.status()).toBe(200)
  const detail = await detailResponse.json()
  expect(detail.status).toBe('success')
  expect(detail.step_results).toHaveLength(2)

  await page.goto(`/executions/${execution.id}`)
  await expect(page.getByRole('heading', { name: 'Execution Detail' })).toBeVisible()
  await expect(page.getByText('success', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('Step 2 passed.')).toBeVisible()
  await expect(page.getByText(new RegExp(`Execution ${execution.id} completed successfully\\.`))).toBeVisible()
})
