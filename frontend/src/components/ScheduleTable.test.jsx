import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import ScheduleTable from './ScheduleTable'

test('renders empty schedule state', () => {
  render(<ScheduleTable schedules={[]} onCancel={() => {}} />)

  expect(screen.getByText('No scheduled executions.')).toBeInTheDocument()
})

test('allows pending schedules to be cancelled but not dispatched schedules', () => {
  const onCancel = vi.fn()
  render(
    <ScheduleTable
      onCancel={onCancel}
      schedules={[
        {
          id: 4,
          project_name: 'Login',
          testcase_title: 'Valid login',
          scheduled_for: '2026-06-10T01:00:00Z',
          status: 'pending',
        },
        {
          id: 5,
          project_name: 'Search',
          testcase_title: 'Search query',
          scheduled_for: '2026-06-10T02:00:00Z',
          status: 'dispatched',
        },
      ]}
    />,
  )

  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(onCancel).toHaveBeenCalledWith(4)
  expect(screen.getAllByRole('button', { name: 'Cancel' })).toHaveLength(1)
  expect(screen.getByText('dispatched')).toBeInTheDocument()
})
