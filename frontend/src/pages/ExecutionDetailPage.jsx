import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'

import StatusPill from '../components/StatusPill'
import { api } from '../lib/api'
import { getAccessToken } from '../lib/authStorage'

function toWebSocketUrl(executionId, token) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/executions/${executionId}/?token=${encodeURIComponent(token)}`
}

export default function ExecutionDetailPage() {
  const { executionId } = useParams()
  const [execution, setExecution] = useState(null)
  const [logs, setLogs] = useState([])
  const [report, setReport] = useState(null)
  const [socketState, setSocketState] = useState('connecting')
  const [error, setError] = useState('')
  const reconnectRef = useRef(null)

  const timeline = useMemo(
    () =>
      [...logs].sort((a, b) => {
        if (!a.created_at || !b.created_at) return 0
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      }),
    [logs],
  )

  useEffect(() => {
    let canceled = false
    const loadInitial = async () => {
      setError('')
      try {
        const [executionData, logsData] = await Promise.all([
          api.get(`/api/executions/${executionId}/`),
          api.get(`/api/execution-logs/?execution_id=${executionId}`),
        ])
        if (!canceled) {
          setExecution(executionData)
          setLogs(logsData || [])
        }
      } catch (err) {
        if (!canceled) setError(err.message || 'Failed to load execution')
      }

      try {
        const reportData = await api.get(`/api/executions/${executionId}/report/`)
        if (!canceled) setReport(reportData)
      } catch {
        if (!canceled) setReport(null)
      }
    }

    loadInitial()
    return () => {
      canceled = true
    }
  }, [executionId])

  useEffect(() => {
    const token = getAccessToken()
    if (!token || !executionId) return undefined

    let socket = null
    let closedManually = false

    const connect = () => {
      setSocketState('connecting')
      socket = new WebSocket(toWebSocketUrl(executionId, token))

      socket.onopen = () => setSocketState('live')
      socket.onclose = () => {
        setSocketState('disconnected')
        if (!closedManually) {
          reconnectRef.current = window.setTimeout(connect, 1600)
        }
      }
      socket.onerror = () => setSocketState('error')
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.execution) {
            setExecution(payload.execution)
          }
          if (payload.log) {
            setLogs((prev) => {
              if (prev.some((item) => item.id === payload.log.id)) return prev
              return [payload.log, ...prev]
            })
          }
          if (payload.report) {
            setReport(payload.report)
          }
        } catch {
          // Ignore malformed websocket payloads in UI.
        }
      }
    }

    connect()

    return () => {
      closedManually = true
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current)
      if (socket) socket.close()
    }
  }, [executionId])

  return (
    <div className="stack-lg">
      <section className="card reveal">
        <div className="card-header">
          <div>
            <p className="brand-eyebrow">Live Monitor</p>
            <h2>Execution Detail</h2>
          </div>
          <span className={`socket-indicator state-${socketState}`}>socket: {socketState}</span>
        </div>

        {error ? <p className="error-text">{error}</p> : null}
        {execution ? (
          <div className="detail-grid">
            <p>
              <span>Project</span>
              {execution.project_name}
            </p>
            <p>
              <span>Test Case</span>
              {execution.testcase_title || '-'}
            </p>
            <p>
              <span>Status</span>
              <StatusPill status={execution.status} />
            </p>
            <p>
              <span>Exit Code</span>
              {execution.exit_code ?? '-'}
            </p>
          </div>
        ) : (
          <p className="muted-text">Loading execution detail...</p>
        )}
      </section>

      <section className="card reveal">
        <h3>Realtime Logs</h3>
        <div className="log-feed">
          {timeline.length === 0 ? (
            <p className="muted-text">No logs yet.</p>
          ) : (
            timeline.map((log) => (
              <article key={log.id} className={`log-line level-${log.level}`}>
                <time>{new Date(log.created_at).toLocaleTimeString()}</time>
                <strong>{log.level}</strong>
                <p>{log.message}</p>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="card reveal">
        <h3>Execution Report</h3>
        {report ? (
          <pre className="report-block">{JSON.stringify(report.report_data, null, 2)}</pre>
        ) : (
          <p className="muted-text">Report is not generated yet.</p>
        )}
      </section>
    </div>
  )
}
