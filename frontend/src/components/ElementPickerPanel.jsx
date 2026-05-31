import { useEffect, useRef, useState } from 'react'

import { api } from '../lib/api'

const terminalStatuses = new Set(['picked', 'error', 'stopped'])

export default function ElementPickerPanel({
  activeStepIndex,
  activeStepTitle,
  suggestedUrl = '',
  suggestedBrowser = 'chromium',
  onPick,
}) {
  const [urlInput, setUrlInput] = useState(suggestedUrl)
  const [session, setSession] = useState(null)
  const [status, setStatus] = useState('Open a real browser picker window to capture an element from any page.')
  const pollTimerRef = useRef(null)
  const sessionIdRef = useRef(null)
  const deliveredPickRef = useRef('')
  const pickerWindowRef = useRef(null)

  useEffect(() => {
    const handleMessage = (event) => {
      if (event.origin !== window.location.origin || event.data?.type !== 'jx-element-picked') return

      onPick({
        target: event.data.target || '',
        selector: event.data.selector || '',
      })
      setSession((prev) => ({
        ...(prev || {}),
        status: 'picked',
        target: event.data.target || '',
        selector: event.data.selector || '',
      }))
      setStatus(`Picked "${event.data.target || 'element'}" for ${activeStepTitle || `step ${activeStepIndex + 1}`}.`)
      pickerWindowRef.current = null
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [activeStepIndex, activeStepTitle, onPick])

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current)
      }
      if (sessionIdRef.current) {
        void api.post(`/api/testcases/picker/${sessionIdRef.current}/stop/`, {}).catch(() => {})
      }
      if (pickerWindowRef.current && !pickerWindowRef.current.closed) {
        pickerWindowRef.current.close()
      }
    }
  }, [])

  useEffect(() => {
    if (!session?.session_id || session.client_picker || terminalStatuses.has(session.status)) {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      return
    }

    pollTimerRef.current = window.setInterval(async () => {
      try {
        const nextSession = await api.get(`/api/testcases/picker/${session.session_id}/`)
        setSession(nextSession)

        if (nextSession.status === 'picked' && deliveredPickRef.current !== nextSession.session_id) {
          deliveredPickRef.current = nextSession.session_id
          onPick({
            target: nextSession.target || '',
            selector: nextSession.selector || '',
          })
          setStatus(`Picked "${nextSession.target || 'element'}" for ${activeStepTitle || `step ${activeStepIndex + 1}`}.`)
        } else if (nextSession.status === 'ready') {
          setStatus('Picker window is ready. Click one element in the visible browser window to capture it.')
        } else if (nextSession.status === 'starting') {
          setStatus('Launching the picker browser window...')
        } else if (nextSession.status === 'error') {
          setStatus(nextSession.error || 'The picker failed to start.')
        } else if (nextSession.status === 'stopped') {
          setStatus('Picker session stopped.')
        }

        if (terminalStatuses.has(nextSession.status) && pollTimerRef.current) {
          window.clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
      } catch (error) {
        setStatus(error.message || 'Failed to poll picker session status.')
        if (pollTimerRef.current) {
          window.clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
      }
    }, 1000)

    return () => {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    }
  }, [activeStepIndex, activeStepTitle, onPick, session?.session_id, session?.status])

  const startPicker = async () => {
    if (activeStepIndex === null || activeStepIndex === undefined) {
      setStatus('Select a step first, then start the picker.')
      return
    }

    const url = urlInput.trim()
    if (!url) {
      setStatus('Enter a page URL before starting the picker.')
      return
    }

    let parsedUrl
    try {
      parsedUrl = new URL(url, window.location.href)
    } catch {
      setStatus('Enter a valid page URL before starting the picker.')
      return
    }

    if (parsedUrl.origin === window.location.origin) {
      if (pickerWindowRef.current && !pickerWindowRef.current.closed) {
        pickerWindowRef.current.close()
      }
      parsedUrl.searchParams.set('__jx_picker', '1')
      const pickerWindow = window.open(parsedUrl.toString(), 'jx-element-picker', 'width=1440,height=900')
      if (!pickerWindow) {
        setStatus('The browser blocked the picker popup. Allow popups for this site and try again.')
        return
      }
      pickerWindowRef.current = pickerWindow
      sessionIdRef.current = null
      setSession({
        session_id: `client-${Date.now()}`,
        status: 'ready',
        browser_name: 'current browser',
        client_picker: true,
      })
      setStatus('Picker window is ready. Click one element in the opened browser window to capture it.')
      return
    }

    try {
      if (sessionIdRef.current) {
        await api.post(`/api/testcases/picker/${sessionIdRef.current}/stop/`, {})
      }
      deliveredPickRef.current = ''
      setStatus('Launching the picker browser window...')
      const nextSession = await api.post('/api/testcases/picker/start/', {
        url,
        browser_name: suggestedBrowser || 'chromium',
      })
      sessionIdRef.current = nextSession.session_id
      setSession(nextSession)
    } catch (error) {
      setStatus(error.message || 'Failed to start the picker.')
    }
  }

  const stopPicker = async () => {
    if (pickerWindowRef.current && !pickerWindowRef.current.closed) {
      pickerWindowRef.current.close()
      pickerWindowRef.current = null
      setSession((prev) => ({ ...(prev || {}), status: 'stopped' }))
      setStatus('Picker session stopped.')
      return
    }

    if (!session?.session_id) return
    try {
      const stopped = await api.post(`/api/testcases/picker/${session.session_id}/stop/`, {})
      setSession(stopped)
      setStatus('Picker session stopped.')
    } catch (error) {
      setStatus(error.message || 'Failed to stop the picker session.')
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h4>Pick Element</h4>
          <p className="muted-text">Start a visible Playwright picker window, then click one element in that browser to fill the active step target and selector.</p>
        </div>
      </div>

      <div className="inline-form">
        <input
          className="picker-url-input"
          value={urlInput}
          onChange={(event) => setUrlInput(event.target.value)}
          placeholder="https://example.com"
        />
        {suggestedUrl ? (
          <button className="button ghost" type="button" onClick={() => setUrlInput(suggestedUrl)}>
            Use Suggested URL
          </button>
        ) : null}
        <button className="button ghost" type="button" onClick={startPicker}>
          Start Picker
        </button>
        <button
          className="button ghost"
          type="button"
          onClick={stopPicker}
          disabled={!session?.session_id || terminalStatuses.has(session.status)}
        >
          Stop Picker
        </button>
      </div>

      <div className="picker-status-panel">
        <p className="muted-text">{status}</p>
        <div className="picker-status-grid">
          <div>
            <span className="picker-status-label">Active step</span>
            <strong>{activeStepTitle || (activeStepIndex !== null && activeStepIndex !== undefined ? `Step ${activeStepIndex + 1}` : 'No step selected')}</strong>
          </div>
          <div>
            <span className="picker-status-label">Browser</span>
            <strong>{session?.browser_name || suggestedBrowser || 'chromium'}</strong>
          </div>
          <div>
            <span className="picker-status-label">Session status</span>
            <strong>{session?.status || 'idle'}</strong>
          </div>
        </div>
        <div className="picker-help-list">
          <p>1. Choose the step you want to fill.</p>
          <p>2. Enter or reuse the page URL.</p>
          <p>3. Click `Start Picker` and wait for the browser window to open.</p>
          <p>4. Click the target element once in that browser window.</p>
        </div>
      </div>
    </div>
  )
}
