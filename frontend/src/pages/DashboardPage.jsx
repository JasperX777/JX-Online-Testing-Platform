import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import StatusPill from '../components/StatusPill'
import { api } from '../lib/api'

export default function DashboardPage() {
  const [projects, setProjects] = useState([])
  const [testcases, setTestcases] = useState([])
  const [executions, setExecutions] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let canceled = false
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [projectsData, testcasesData, executionsData, analyticsData] = await Promise.all([
          api.get('/api/projects/'),
          api.get('/api/testcases/'),
          api.get('/api/executions/'),
          api.get('/api/executions/analytics/'),
        ])
        if (!canceled) {
          setProjects(projectsData || [])
          setTestcases(testcasesData || [])
          setExecutions(executionsData || [])
          setAnalytics(analyticsData)
        }
      } catch (err) {
        if (!canceled) setError(err.message || 'Failed to load dashboard data')
      } finally {
        if (!canceled) setLoading(false)
      }
    }

    load()
    return () => {
      canceled = true
    }
  }, [])

  const stats = useMemo(() => {
    const successCount = executions.filter((item) => item.status === 'success').length
    const failedCount = executions.filter((item) => item.status === 'failed').length
    const runningCount = executions.filter((item) => item.status === 'running').length
    return [
      { label: 'Projects', value: projects.length.toString() },
      { label: 'Test Cases', value: testcases.length.toString() },
      { label: 'Executions', value: executions.length.toString() },
      { label: 'Success / Failed / Running', value: `${successCount} / ${failedCount} / ${runningCount}` },
    ]
  }, [projects, testcases, executions])

  const recentExecutions = executions.slice(0, 6)
  const trendMax = Math.max(...(analytics?.trend || []).map((item) => item.total), 1)

  return (
    <div className="stack-lg">
      <section className="card reveal">
        <div className="card-header">
          <div>
            <p className="brand-eyebrow">Mission Overview</p>
            <h2>Dashboard</h2>
          </div>
          <Link className="button ghost" to="/executions">
            Open Execution Center
          </Link>
        </div>

        {loading ? <p className="muted-text">Loading dashboard metrics...</p> : null}
        {error ? <p className="error-text">{error}</p> : null}

        <div className="stat-grid">
          {stats.map((stat, index) => (
            <article className="stat-card" key={stat.label} style={{ animationDelay: `${index * 90}ms` }}>
              <p>{stat.label}</p>
              <h3>{stat.value}</h3>
            </article>
          ))}
        </div>
      </section>

      <section className="card reveal">
        <div className="card-header">
          <div>
            <h3>Seven-day Execution Trend</h3>
            <p className="muted-text">Completed pass rate: {analytics?.pass_rate ?? 0}%</p>
          </div>
        </div>
        <div className="trend-chart" aria-label="Execution totals for the last seven days">
          {(analytics?.trend || []).map((item) => (
            <div className="trend-column" key={item.date}>
              <div className="trend-bar-track" title={`${item.total} total, ${item.success} successful, ${item.failed} failed`}>
                <div className="trend-bar" style={{ height: `${Math.max((item.total / trendMax) * 100, item.total ? 8 : 0)}%` }} />
              </div>
              <strong>{item.total}</strong>
              <span>{item.date.slice(5)}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="card reveal">
        <div className="card-header">
          <h3>Recent Executions</h3>
          <Link className="inline-link" to="/executions">
            See all
          </Link>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Test Case</th>
                <th>Status</th>
                <th>Result</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {recentExecutions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted-cell">
                    No execution history yet.
                  </td>
                </tr>
              ) : (
                recentExecutions.map((execution) => (
                  <tr key={execution.id}>
                    <td>{execution.project_name}</td>
                    <td>{execution.testcase_title || '-'}</td>
                    <td>
                      <StatusPill status={execution.status} />
                    </td>
                    <td className="summary-cell">
                      <span className="truncate-text" title={execution.result_summary || '-'}>
                        {execution.result_summary || '-'}
                      </span>
                    </td>
                    <td>
                      <Link className="inline-link" to={`/executions/${execution.id}`}>
                        Detail
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
