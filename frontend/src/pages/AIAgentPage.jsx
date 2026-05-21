import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import ActionModal from '../components/ActionModal'
import StatusPill from '../components/StatusPill'
import { api } from '../lib/api'

const starterPrompts = [
  'Generate login test cases for Login Project and run them',
  'Generate registration test cases for Shopping Project',
  'Create search test cases only',
]

function formatTime(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export default function AIAgentPage() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')
  const [lastResult, setLastResult] = useState(null)
  const [sessionMenu, setSessionMenu] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const messagesEndRef = useRef(null)
  const optimisticIdRef = useRef(0)

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) || null,
    [sessions, activeSessionId],
  )

  const loadSessions = useCallback(async (preferredSessionId = null, { selectFallback = false } = {}) => {
    const data = await api.get('/api/ai-agent/sessions/')
    setSessions(data || [])
    const nextSession = data?.find((session) => session.id === preferredSessionId) || (selectFallback ? data?.[0] : null)
    if (nextSession) {
      setActiveSessionId(nextSession.id)
      setMessages(nextSession.messages || [])
    } else if (!data?.length || preferredSessionId) {
      setActiveSessionId(null)
      setMessages([])
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        setError('')
        await loadSessions(null, { selectFallback: true })
      } catch (err) {
        setError(err.message || 'Failed to load AI Agent history')
      }
    })()
  }, [loadSessions])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  useEffect(() => {
    if (!sessionMenu) return undefined

    const closeMenu = () => setSessionMenu(null)
    window.addEventListener('click', closeMenu)
    window.addEventListener('scroll', closeMenu, true)
    return () => {
      window.removeEventListener('click', closeMenu)
      window.removeEventListener('scroll', closeMenu, true)
    }
  }, [sessionMenu])

  const selectSession = (session) => {
    setActiveSessionId(session.id)
    setMessages(session.messages || [])
    setLastResult(null)
    setError('')
    setSessionMenu(null)
  }

  const startNewSession = () => {
    setActiveSessionId(null)
    setMessages([])
    setLastResult(null)
    setError('')
    setSessionMenu(null)
  }

  const deleteSession = async (session) => {
    if (!session) return
    setError('')
    try {
      await api.del(`/api/ai-agent/sessions/${session.id}/`)
      const nextSessions = sessions.filter((item) => item.id !== session.id)
      setSessions(nextSessions)
      if (session.id === activeSessionId) {
        setActiveSessionId(null)
        setMessages([])
        setLastResult(null)
      }
      await loadSessions(session.id === activeSessionId ? null : activeSessionId)
    } catch (err) {
      setError(err.message || 'Failed to delete AI Agent conversation')
    } finally {
      setDeleteTarget(null)
      setSessionMenu(null)
    }
  }

  const openSessionMenu = (event, session) => {
    event.preventDefault()
    setSessionMenu({
      session,
      x: event.clientX,
      y: event.clientY,
    })
  }

  const sendMessage = async (event, overrideMessage) => {
    event?.preventDefault()
    const message = (overrideMessage ?? input).trim()
    if (!message || isSending) return

    setIsSending(true)
    setError('')
    setInput('')
    optimisticIdRef.current += 1
    const optimisticMessage = {
      id: `local-${optimisticIdRef.current}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
      metadata: {},
    }
    setMessages((prev) => [...prev, optimisticMessage])

    try {
      const payload = await api.post('/api/ai-agent/chat/', {
        session_id: activeSessionId,
        message,
      })
      setActiveSessionId(payload.session.id)
      setMessages(payload.session.messages || [])
      setLastResult(payload)
      await loadSessions(payload.session.id)
    } catch (err) {
      setError(err.message || 'AI Agent request failed')
      setMessages((prev) => prev.filter((item) => item.id !== optimisticMessage.id))
      setInput(message)
    } finally {
      setIsSending(false)
    }
  }

  const sendProjectCandidate = (project) => {
    void sendMessage(null, project.name)
  }

  const handleComposerKeyDown = (event) => {
    if (event.key !== 'Enter' || event.shiftKey) return
    event.preventDefault()
    void sendMessage(event)
  }

  return (
    <div className="ai-agent-page">
      <section className="card reveal ai-agent-shell">
        <aside className="ai-session-list">
          <div className="ai-session-header">
            <div>
              <p className="header-label">Mock Agent</p>
              <h2>AI Agent</h2>
            </div>
            <button className="button ghost" type="button" onClick={startNewSession}>
              New
            </button>
          </div>

          <div className="ai-session-items">
            {sessions.length === 0 ? (
              <p className="muted-text">No conversations yet.</p>
            ) : (
              sessions.map((session) => (
                <div
                  className={`ai-session-item ${session.id === activeSessionId ? 'active' : ''}`}
                  key={session.id}
                  onContextMenu={(event) => openSessionMenu(event, session)}
                >
                  <button className="ai-session-select" type="button" onClick={() => selectSession(session)}>
                    <span>{session.title || 'AI Agent conversation'}</span>
                    <small>{session.project_name || 'No project confirmed'}</small>
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        <section className="ai-chat-panel">
          <div className="ai-chat-header">
            <div>
              <h3>{activeSession?.project_name || 'Project-aware test generation'}</h3>
              <p className="muted-text">Describe the project and testing goal. The mock agent will create executable test cases.</p>
            </div>
          </div>

          <div className="ai-message-feed">
            {messages.length === 0 ? (
              <div className="ai-empty-state">
                <h3>Start with the project name and what to test.</h3>
                <div className="ai-prompt-row">
                  {starterPrompts.map((prompt) => (
                    <button className="button ghost" key={prompt} type="button" onClick={(event) => sendMessage(event, prompt)}>
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <article className={`ai-message ${message.role}`} key={message.id}>
                  <div className="ai-message-bubble">
                    <p>{message.content}</p>
                    {message.metadata?.project_candidates?.length ? (
                      <div className="ai-candidate-row">
                        {message.metadata.project_candidates.map((project) => (
                          <button
                            className="button ghost"
                            key={project.id}
                            type="button"
                            onClick={() => sendProjectCandidate(project)}
                            disabled={isSending}
                          >
                            {project.name}
                          </button>
                        ))}
                      </div>
                    ) : null}
                    <time>{formatTime(message.created_at)}</time>
                  </div>
                </article>
              ))
            )}
            {isSending ? (
              <article className="ai-message assistant">
                <div className="ai-message-bubble">
                  <p>Thinking through the mock agent flow...</p>
                </div>
              </article>
            ) : null}
            <div ref={messagesEndRef} />
          </div>

          {lastResult?.generated_testcases?.length ? (
            <div className="ai-result-panel">
              <div className="ai-result-header">
                <h3>Generated Test Cases</h3>
                {lastResult.auto_run ? <span className="socket-indicator state-live">Auto run started</span> : null}
              </div>
              <div className="ai-generated-grid">
                {lastResult.generated_testcases.map((testcase) => (
                  <div className="ai-generated-item" key={testcase.id}>
                    <strong>{testcase.title}</strong>
                    <span>{testcase.steps_json?.length || 0} steps</span>
                  </div>
                ))}
              </div>
              {lastResult.executions?.length ? (
                <div className="ai-execution-row">
                  {lastResult.executions.map((execution) => (
                    <Link className="ai-execution-link" key={execution.id} to={`/executions/${execution.id}`}>
                      <StatusPill status={execution.status} />
                      <span>{execution.testcase_title}</span>
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {error ? <p className="error-text">{error}</p> : null}

          <form className="ai-compose" onSubmit={sendMessage}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Example: Generate login test cases for Online Testing Platform and run them"
              disabled={isSending}
            />
            <button className="button primary" type="submit" disabled={isSending || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      </section>

      {sessionMenu ? (
        <div
          className="ai-session-menu"
          style={{ left: sessionMenu.x, top: sessionMenu.y }}
          onClick={(event) => event.stopPropagation()}
        >
          <button
            className="ai-session-menu-item danger"
            type="button"
            onClick={() => {
              setDeleteTarget(sessionMenu.session)
              setSessionMenu(null)
            }}
          >
            Delete
          </button>
        </div>
      ) : null}

      <ActionModal
        open={Boolean(deleteTarget)}
        title="Delete Conversation"
        description={`Delete "${deleteTarget?.title || 'AI Agent conversation'}"? This will permanently remove the chat history.`}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteSession(deleteTarget)}
        confirmText="Delete"
        danger
      />
    </div>
  )
}
