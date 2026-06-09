import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import ActionModal from '../components/ActionModal'
import StatusPill from '../components/StatusPill'
import { api } from '../lib/api'
import { getAccessToken } from '../lib/authStorage'

function toProjectWebSocketUrl(projectId, token) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/projects/${projectId}/executions/?token=${encodeURIComponent(token)}`
}

export default function ExecutionsPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [testcases, setTestcases] = useState([])
  const [executions, setExecutions] = useState([])
  const [schedules, setSchedules] = useState([])
  const [projectCaseCounts, setProjectCaseCounts] = useState({})
  const [projectId, setProjectId] = useState('')
  const [testcaseId, setTestcaseId] = useState('')
  const [scheduledFor, setScheduledFor] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const socketRefs = useRef({})
  const reconnectRefs = useRef({})

  const filteredTestcases = useMemo(() => testcases, [testcases])

  const loadData = async () => {
    const [projectData, executionData, allTestcasesData, scheduleData] = await Promise.all([
      api.get('/api/projects/'),
      api.get('/api/executions/'),
      api.get('/api/testcases/'),
      api.get('/api/execution-schedules/'),
    ])
    setProjects(projectData || [])
    setExecutions(executionData || [])
    setSchedules(scheduleData || [])
    const counts = {}
    ;(allTestcasesData || []).forEach((item) => {
      counts[item.project] = (counts[item.project] || 0) + 1
    })
    setProjectCaseCounts(counts)
  }

  const loadTestcasesForProject = async (selectedProjectId) => {
    if (!selectedProjectId) {
      setTestcases([])
      return
    }
    const data = await api.get(`/api/testcases/?project_id=${selectedProjectId}`)
    setTestcases(data || [])
  }

  useEffect(() => {
    ;(async () => {
      try {
        setError('')
        await loadData()
      } catch (err) {
        setError(err.message || 'Failed to load execution center')
      }
    })()
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        setError('')
        setTestcaseId('')
        await loadTestcasesForProject(projectId)
      } catch (err) {
        setError(err.message || 'Failed to load test cases for selected project')
      }
    })()
  }, [projectId])

  useEffect(() => {
    const token = getAccessToken()
    if (!token || projects.length === 0) return undefined

    const sockets = socketRefs.current
    const reconnects = reconnectRefs.current
    const activeProjectIds = new Set(projects.map((project) => String(project.id)))

    const cleanupProjectSocket = (currentProjectId) => {
      const existing = sockets[currentProjectId]
      if (existing) {
        existing.__closedManually = true
        existing.close()
        delete sockets[currentProjectId]
      }
      if (reconnects[currentProjectId]) {
        window.clearTimeout(reconnects[currentProjectId])
        delete reconnects[currentProjectId]
      }
    }

    const upsertExecution = (incoming) => {
      setExecutions((prev) => {
        const idx = prev.findIndex((item) => item.id === incoming.id)
        if (idx === -1) return [incoming, ...prev]
        const next = [...prev]
        next[idx] = { ...next[idx], ...incoming }
        return next
      })
    }

    const connectProjectSocket = (currentProjectId) => {
      const socket = new WebSocket(toProjectWebSocketUrl(currentProjectId, token))
      socket.__closedManually = false
      sockets[currentProjectId] = socket

      socket.onclose = () => {
        if (socket.__closedManually) return
        reconnects[currentProjectId] = window.setTimeout(() => {
          connectProjectSocket(currentProjectId)
        }, 1500)
      }

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.execution) {
            upsertExecution(payload.execution)
          }
        } catch {
          // Ignore malformed websocket payloads.
        }
      }
    }

    projects.forEach((project) => {
      const currentProjectId = String(project.id)
      if (!sockets[currentProjectId]) {
        connectProjectSocket(currentProjectId)
      }
    })

    Object.keys(sockets).forEach((currentProjectId) => {
      if (!activeProjectIds.has(currentProjectId)) {
        cleanupProjectSocket(currentProjectId)
      }
    })

    return () => {
      Object.keys(sockets).forEach((currentProjectId) => {
        cleanupProjectSocket(currentProjectId)
      })
    }
  }, [projects])

  const runExecution = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      const execution = await api.post('/api/executions/run/', {
        project: Number(projectId),
        testcase: Number(testcaseId),
      })
      setMessage('Execution started.')
      await loadData()
      await loadTestcasesForProject(projectId)
      navigate(`/executions/${execution.id}`)
    } catch (err) {
      setError(err.message || 'Execution request failed')
    }
  }

  const scheduleExecution = async () => {
    setError('')
    setMessage('')
    try {
      await api.post('/api/execution-schedules/', {
        project: Number(projectId),
        testcase: Number(testcaseId),
        scheduled_for: new Date(scheduledFor).toISOString(),
      })
      setMessage('Execution scheduled.')
      setScheduledFor('')
      await loadData()
    } catch (err) {
      setError(err.message || 'Scheduling request failed')
    }
  }

  const cancelSchedule = async (scheduleId) => {
    setError('')
    setMessage('')
    try {
      await api.post(`/api/execution-schedules/${scheduleId}/cancel/`, {})
      setMessage('Schedule cancelled.')
      await loadData()
    } catch (err) {
      setError(err.message || 'Cancel schedule failed')
    }
  }

  const closeDeleteModal = () => setDeleteTarget(null)

  const deleteExecution = async () => {
    if (!deleteTarget) return
    setError('')
    setMessage('')
    try {
      await api.del(`/api/executions/${deleteTarget.id}/`)
      setMessage('Execution deleted.')
      closeDeleteModal()
      await loadData()
      await loadTestcasesForProject(projectId)
    } catch (err) {
      setError(err.message || 'Delete execution failed')
    }
  }

  return (
    <div className="stack-lg">
      <section className="card reveal">
        <div className="card-header">
          <h2>Execution Center</h2>
          <p className="muted-text">Start automated browser runs and track each structured test execution.</p>
        </div>

        <form className="inline-form" onSubmit={runExecution}>
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)} required>
            <option value="">Select project</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name} ({projectCaseCounts[project.id] || 0} test cases)
              </option>
            ))}
          </select>
          <select value={testcaseId} onChange={(event) => setTestcaseId(event.target.value)} required>
            <option value="">Select test case</option>
            {projectId && filteredTestcases.length === 0 ? (
              <option value="" disabled>
                No test cases under this project
              </option>
            ) : null}
            {filteredTestcases.map((testcase) => (
              <option key={testcase.id} value={testcase.id}>
                {testcase.title}
              </option>
            ))}
          </select>
          <button className="button primary" type="submit">
            Run Execution
          </button>
          <input
            aria-label="Scheduled execution time"
            type="datetime-local"
            value={scheduledFor}
            onChange={(event) => setScheduledFor(event.target.value)}
          />
          <button
            className="button ghost"
            type="button"
            disabled={!projectId || !testcaseId || !scheduledFor}
            onClick={scheduleExecution}
          >
            Schedule
          </button>
        </form>

        {message ? <p className="success-text">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="card reveal">
        <h3>Scheduled Executions</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Test Case</th>
                <th>Scheduled For</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {schedules.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted-cell">No scheduled executions.</td>
                </tr>
              ) : schedules.map((schedule) => (
                <tr key={schedule.id}>
                  <td>{schedule.project_name}</td>
                  <td>{schedule.testcase_title}</td>
                  <td>{new Date(schedule.scheduled_for).toLocaleString()}</td>
                  <td><StatusPill status={schedule.status} /></td>
                  <td>
                    {schedule.status === 'pending' ? (
                      <button className="button danger" type="button" onClick={() => cancelSchedule(schedule.id)}>
                        Cancel
                      </button>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card reveal">
        <h3>Execution History</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Test Case</th>
                <th>Status</th>
                <th>Current Step</th>
                <th>Failed Step</th>
                <th>Summary</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {executions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="muted-cell">
                    No executions yet.
                  </td>
                </tr>
              ) : (
                executions.map((execution) => (
                  <tr key={execution.id}>
                    <td>{execution.project_name}</td>
                    <td>{execution.testcase_title || '-'}</td>
                    <td>
                      <StatusPill status={execution.status} />
                    </td>
                    <td>{execution.current_step_no ?? '-'}</td>
                    <td>{execution.failed_step_no ?? '-'}</td>
                    <td className="summary-cell">
                      <span className="truncate-text" title={execution.failure_reason || execution.result_summary || '-'}>
                        {execution.failure_reason || execution.result_summary || '-'}
                      </span>
                    </td>
                    <td className="action-cell">
                      <div className="action-row">
                        <Link className="inline-link" to={`/executions/${execution.id}`}>
                          Detail
                        </Link>
                        <button
                          className="button danger"
                          type="button"
                          onClick={() => setDeleteTarget(execution)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <ActionModal
        open={Boolean(deleteTarget)}
        title="Delete Execution"
        description="This execution record will be permanently removed."
        onCancel={closeDeleteModal}
        onConfirm={deleteExecution}
        confirmText="Delete"
        danger
      />
    </div>
  )
}
