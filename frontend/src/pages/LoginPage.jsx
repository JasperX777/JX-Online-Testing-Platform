import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { registerUser } from '../lib/api'

const modes = {
  signIn: 'signIn',
  register: 'register',
}

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [mode, setMode] = useState(modes.signIn)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const from = location.state?.from?.pathname || '/'

  if (isAuthenticated) {
    return <Navigate to={from} replace />
  }

  const onSignIn = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setMessage('')
    try {
      await login(username, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  const onRegister = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setMessage('')
    try {
      await registerUser({ username, email, password })
      setMessage('Account created. Signing you in...')
      await login(username, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fullscreen-center auth-screen">
      <div className="auth-panel reveal">
        <p className="brand-eyebrow">JX Platform</p>
        <h1>{mode === modes.signIn ? 'Control Room Login' : 'Create Account'}</h1>
        <p className="muted-text">
          {mode === modes.signIn
            ? 'Sign in with your backend account to manage executions and live logs.'
            : 'Register a user account directly from the UI.'}
        </p>

        <div className="mode-switch" role="tablist" aria-label="auth mode">
          <button
            type="button"
            className={`mode-tab ${mode === modes.signIn ? 'active' : ''}`}
            onClick={() => {
              setMode(modes.signIn)
              setError('')
              setMessage('')
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`mode-tab ${mode === modes.register ? 'active' : ''}`}
            onClick={() => {
              setMode(modes.register)
              setError('')
              setMessage('')
            }}
          >
            Register
          </button>
        </div>

        <form className="form-grid" onSubmit={mode === modes.signIn ? onSignIn : onRegister}>
          <label className="field">
            Username
            <input value={username} onChange={(event) => setUsername(event.target.value)} required />
          </label>

          {mode === modes.register ? (
            <label className="field">
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
          ) : null}

          <label className="field">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>


          {message ? <p className="success-text">{message}</p> : null}
          {error ? <p className="error-text">{error}</p> : null}

          <button className="button primary" disabled={submitting} type="submit">
            {submitting
              ? mode === modes.signIn
                ? 'Signing in...'
                : 'Creating...'
              : mode === modes.signIn
                ? 'Sign in'
                : 'Create account'}
          </button>
        </form>
      </div>
    </div>
  )
}
