import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import StatusPill from '../components/StatusPill'
import { api } from '../lib/api'
import { getAccessToken } from '../lib/authStorage'

function toWebSocketUrl(executionId, token) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/executions/${executionId}/?token=${encodeURIComponent(token)}`
}

function formatStep(step) {
  const title = step.step_title ? `${step.step_title}: ` : ''
  switch (step.action) {
    case 'launch_browser':
      return `${title}${step.description || `Launch the ${step.value || 'chromium'} browser.`}`
    case 'open_page':
      return `${title}${step.description || `Open "${step.target}" at "${step.value}"`}`
    case 'click_button':
      return `${title}${step.description || `Click "${step.target}"`}`
    case 'input_text':
      return `${title}${step.description || `Type "${step.value || ''}" into "${step.target}"`}`
    case 'press_key':
      return `${title}${step.description || `Press the ${step.value || 'configured'} key.`}`
    case 'verify_element':
      return `${title}${step.description || `Verify "${step.target}" is visible`}`
    default:
      return `${title}${step.description || `${step.action} - ${step.target}`}`
  }
}

export default function ExecutionDetailPage() {
  const { executionId } = useParams()
  const navigate = useNavigate()
  const [execution, setExecution] = useState(null)
  const [logs, setLogs] = useState([])
  const [report, setReport] = useState(null)
  const [socketState, setSocketState] = useState('connecting')
  const [error, setError] = useState('')
  const reconnectRef = useRef(null)

  const stepResults = useMemo(() => execution?.step_results || [], [execution])
  const reportData = report?.report_data || null
  const reportSummary = reportData?.summary || null
  const reportExecution = reportData?.execution || null
  const executionVideoUrl = execution?.video_url || reportExecution?.video_url || ''

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
        const reportDataResponse = await api.get(`/api/executions/${executionId}/report/`)
        if (!canceled) setReport(reportDataResponse)
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
    <div className="stack-lg execution-detail-page">
      <section className="card reveal">
        <div className="card-header">
          <div>
            <p className="brand-eyebrow">Automation Runner</p>
            <h2>Execution Detail</h2>
          </div>
          <div className="inline-form detail-header-actions">
            <button
              className="button ghost"
              type="button"
              onClick={() => {
                if (window.history.length > 1) {
                  navigate(-1)
                  return
                }
                navigate('/executions')
              }}
            >
              Back
            </button>
            <span className={`socket-indicator state-${socketState}`}>socket: {socketState}</span>
          </div>
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
              <span>Module</span>
              {execution.testcase_module || '-'}
            </p>
            <p>
              <span>Scenario</span>
              {execution.testcase_scenario || '-'}
            </p>
            <p>
              <span>Status</span>
              <StatusPill status={execution.status} />
            </p>
            <p>
              <span>Current Step</span>
              {execution.current_step_no ?? '-'}
            </p>
            <p>
              <span>Failed Step</span>
              {execution.failed_step_no ?? '-'}
            </p>
            <p>
              <span>Failure Reason</span>
              {execution.failure_reason || '-'}
            </p>
          </div>
        ) : (
          <p className="muted-text">Loading execution detail...</p>
        )}
      </section>

      <section className="card reveal">
        <div className="card-header">
          <div>
            <h3>Step Results</h3>
            <p className="muted-text">Each step is executed automatically in a headless browser.</p>
          </div>
        </div>

        {stepResults.length === 0 ? (
          <p className="muted-text">No steps recorded for this execution.</p>
        ) : (
          <div className="stack-md">
            {stepResults.map((step) => (
              <article key={step.id} className={`card ${execution?.current_step_no === step.step_no ? 'reveal' : ''}`}>
                <div className="card-header">
                  <strong>Step {step.step_no}{step.step_title ? ` - ${step.step_title}` : ''}</strong>
                  <StatusPill status={step.status} />
                </div>
                <p>{formatStep(step)}</p>
                {step.action === 'launch_browser' || step.action === 'press_key' ? null : <p className="muted-text">Target: {step.target || '-'}</p>}
                {step.value ? <p className="muted-text">Value: {step.value}</p> : null}
                {step.note ? <p className="muted-text">Case note: {step.note}</p> : null}
                {step.error_message ? <p className="error-text">Error: {step.error_message}</p> : null}
                {step.screenshot_url ? (
                  <p>
                    <a className="inline-link" href={step.screenshot_url} target="_blank" rel="noreferrer">
                      Open failure screenshot
                    </a>
                  </p>
                ) : null}
                <details>
                  <summary>Automation details</summary>
                  <p className="muted-text">Locator type: {step.locator_type || 'css'}</p>
                  <p className="muted-text">Selector: {step.selector || '-'}</p>
                </details>
                <p className="muted-text">Executed at: {step.executed_at ? new Date(step.executed_at).toLocaleString() : '-'}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="card reveal">
        <h3>Execution Logs</h3>
        <div className="log-feed">
          {logs.length === 0 ? (
            <p className="muted-text">No logs yet.</p>
          ) : (
            [...logs]
              .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
              .map((log) => (
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
        {reportSummary && reportExecution ? (
          <div className="stack-sm">
            <p>
              <strong>Final status:</strong> {reportExecution.status}
            </p>
            <p>
              <strong>Total steps:</strong> {reportSummary.total_steps}
            </p>
            <p>
              <strong>Passed steps:</strong> {reportSummary.passed_steps}
            </p>
            <p>
              <strong>Failed steps:</strong> {reportSummary.failed_steps}
            </p>
            <p>
              <strong>Pending steps:</strong> {reportSummary.pending_steps}
            </p>
            <p>
              <strong>Failure reason:</strong> {reportSummary.failure_reason || '-'}
            </p>
          </div>
        ) : reportData ? (
          <div className="stack-sm">
            <p className="muted-text">This execution uses a legacy report format.</p>
            <pre className="report-block">{JSON.stringify(reportData, null, 2)}</pre>
          </div>
        ) : (
          <p className="muted-text">Report is not generated yet.</p>
        )}
      </section>

      <section className="card reveal">
        <div className="card-header">
          <div>
            <h3>Execution Recording</h3>
            <p className="muted-text">Watch the browser run that produced this result.</p>
          </div>
        </div>
        {executionVideoUrl ? (
          <div className="stack-sm">
            <div className="execution-video-frame">
              <video key={executionVideoUrl} controls preload="metadata" src={executionVideoUrl}>
                Your browser does not support embedded video playback.
              </video>
            </div>
            <a className="inline-link" href={executionVideoUrl} target="_blank" rel="noreferrer">
              Open recording
            </a>
          </div>
        ) : (
          <p className="muted-text">Recording will appear here after the automated run finishes.</p>
        )}
      </section>
    </div>
  )
}
