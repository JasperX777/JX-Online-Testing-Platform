import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import DashboardPage from './DashboardPage'
import ExecutionsPage from './ExecutionsPage'
import LoginPage from './LoginPage'
import ProjectsPage from './ProjectsPage'

const { apiMock, loginMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
  loginMock: vi.fn(),
}))

vi.mock('../lib/api', () => ({
  api: apiMock,
  registerUser: vi.fn(),
}))
vi.mock('../lib/authStorage', () => ({
  getAccessToken: () => '',
}))
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    login: loginMock,
    isAuthenticated: false,
  }),
}))

class WebSocketMock {
  close() {}
}

beforeEach(() => {
  apiMock.get.mockReset()
  apiMock.post.mockReset()
  apiMock.put.mockReset()
  apiMock.del.mockReset()
  loginMock.mockReset()
  vi.stubGlobal('WebSocket', WebSocketMock)
})

test('login page submits credentials and navigates to the dashboard', async () => {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  )

  await userEvent.type(screen.getByLabelText('Username'), 'Jasper')
  await userEvent.type(screen.getByLabelText('Password'), 'secret')
  await userEvent.click(screen.getByRole('button', { name: 'Sign in', exact: true }))

  expect(loginMock).toHaveBeenCalledWith('Jasper', 'secret')
})

test('dashboard loads metrics, analytics, and recent executions', async () => {
  apiMock.get.mockImplementation((path) => {
    if (path === '/api/projects/') return Promise.resolve([{ id: 1 }])
    if (path === '/api/testcases/') return Promise.resolve([{ id: 2 }])
    if (path === '/api/executions/analytics/') {
      return Promise.resolve({
        pass_rate: 100,
        trend: [{ date: '2026-06-10', total: 1, success: 1, failed: 0 }],
      })
    }
    return Promise.resolve([
      {
        id: 3,
        project_name: 'Platform',
        testcase_title: 'Login',
        status: 'success',
        result_summary: 'Execution completed successfully.',
      },
    ])
  })

  render(<MemoryRouter><DashboardPage /></MemoryRouter>)

  expect(await screen.findByText('Completed pass rate: 100%')).toBeInTheDocument()
  expect(screen.getByText('Execution completed successfully.')).toBeInTheDocument()
  expect(screen.getByText('1 / 0 / 0')).toBeInTheDocument()
})

test('projects page creates a project and refreshes the list', async () => {
  apiMock.get
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce([
      {
        id: 4,
        name: 'Automation',
        description: 'Browser tests',
        owner_username: 'Jasper',
        created_at: '2026-06-10T00:00:00Z',
      },
    ])
  apiMock.post.mockResolvedValue({ id: 4 })

  render(<ProjectsPage />)
  await userEvent.type(screen.getByPlaceholderText('Project name'), 'Automation')
  await userEvent.type(screen.getByPlaceholderText('Description'), 'Browser tests')
  await userEvent.click(screen.getByRole('button', { name: 'Create' }))

  expect(await screen.findByText('Project created.')).toBeInTheDocument()
  expect(screen.getByText('Automation')).toBeInTheDocument()
  expect(apiMock.post).toHaveBeenCalledWith('/api/projects/', {
    name: 'Automation',
    description: 'Browser tests',
  })
})

test('execution centre schedules and cancels a test run', async () => {
  apiMock.get.mockImplementation((path) => {
    if (path === '/api/projects/') return Promise.resolve([{ id: 1, name: 'Platform' }])
    if (path.startsWith('/api/testcases/?')) return Promise.resolve([{ id: 2, project: 1, title: 'Login' }])
    if (path === '/api/testcases/') return Promise.resolve([{ id: 2, project: 1, title: 'Login' }])
    if (path === '/api/execution-schedules/') return Promise.resolve([])
    return Promise.resolve([])
  })
  apiMock.post.mockResolvedValue({ id: 9 })

  render(<MemoryRouter><ExecutionsPage /></MemoryRouter>)

  const selects = await screen.findAllByRole('combobox')
  fireEvent.change(selects[0], { target: { value: '1' } })
  await waitFor(() => expect(selects[1].querySelector('option[value="2"]')).toBeTruthy())
  fireEvent.change(selects[1], { target: { value: '2' } })
  fireEvent.change(screen.getByLabelText('Scheduled execution time'), { target: { value: '2027-06-12T10:30' } })
  await userEvent.click(screen.getByRole('button', { name: 'Schedule' }))

  expect(await screen.findByText('Execution scheduled.')).toBeInTheDocument()
  expect(apiMock.post).toHaveBeenCalledWith('/api/execution-schedules/', expect.objectContaining({
    project: 1,
    testcase: 2,
  }))
})
