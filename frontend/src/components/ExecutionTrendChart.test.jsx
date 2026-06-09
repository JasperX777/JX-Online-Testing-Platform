import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import ExecutionTrendChart from './ExecutionTrendChart'

test('renders pass rate and seven-day execution totals', () => {
  const trend = Array.from({ length: 7 }, (_, index) => ({
    date: `2026-06-${String(index + 1).padStart(2, '0')}`,
    total: index,
    success: Math.max(index - 1, 0),
    failed: index ? 1 : 0,
  }))

  render(<ExecutionTrendChart analytics={{ pass_rate: 75, trend }} />)

  expect(screen.getByText('Completed pass rate: 75%')).toBeInTheDocument()
  expect(screen.getByLabelText('Execution totals for the last seven days').children).toHaveLength(7)
  expect(screen.getByTitle('6 total, 5 successful, 1 failed')).toBeInTheDocument()
})

test('renders an empty chart before analytics load', () => {
  render(<ExecutionTrendChart analytics={null} />)

  expect(screen.getByText('Completed pass rate: 0%')).toBeInTheDocument()
  expect(screen.getByLabelText('Execution totals for the last seven days')).toBeEmptyDOMElement()
})
