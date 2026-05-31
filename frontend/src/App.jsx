import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import AppShell from './components/AppShell'
import ProtectedRoute from './components/ProtectedRoute'
import AIAgentPage from './pages/AIAgentPage'
import DashboardPage from './pages/DashboardPage'
import ExecutionDetailPage from './pages/ExecutionDetailPage'
import ExecutionsPage from './pages/ExecutionsPage'
import LoginPage from './pages/LoginPage'
import ProjectsPage from './pages/ProjectsPage'
import TestCaseListPage from './pages/TestCaseListPage'
import TestCasesPage from './pages/TestCasesPage'

function escapeCssValue(value) {
  if (window.CSS && typeof window.CSS.escape === 'function') {
    return window.CSS.escape(value)
  }
  return String(value).replace(/["\\]/g, '\\$&')
}

function buildFriendlyLabel(element) {
  const ariaLabel = element.getAttribute('aria-label')
  const placeholder = element.getAttribute('placeholder')
  const name = element.getAttribute('name')
  const id = element.getAttribute('id')
  const text = (element.textContent || '').trim()

  return ariaLabel || placeholder || name || id || text.slice(0, 40) || `${element.tagName.toLowerCase()} element`
}

function buildSelector(element) {
  const id = element.getAttribute('id')
  if (id) return `#${escapeCssValue(id)}`

  const name = element.getAttribute('name')
  if (name) return `${element.tagName.toLowerCase()}[name="${escapeCssValue(name)}"]`

  const dataTestId = element.getAttribute('data-testid')
  if (dataTestId) return `${element.tagName.toLowerCase()}[data-testid="${escapeCssValue(dataTestId)}"]`

  const classes = [...element.classList].filter(Boolean)
  if (classes.length > 0) {
    return `${element.tagName.toLowerCase()}.${classes.slice(0, 2).map(escapeCssValue).join('.')}`
  }

  return element.tagName.toLowerCase()
}

function useClientElementPicker() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('__jx_picker') !== '1') return undefined

    let activeElement = null
    let previousOutline = ''
    const banner = document.createElement('div')
    banner.textContent = 'Picker mode: click one element to send its selector back.'
    banner.style.cssText = [
      'position:fixed',
      'left:16px',
      'right:16px',
      'bottom:16px',
      'z-index:2147483647',
      'padding:12px 14px',
      'border-radius:8px',
      'background:#102a43',
      'color:#fff',
      'font:14px system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
      'box-shadow:0 12px 32px rgba(0,0,0,.22)',
      'pointer-events:none',
    ].join(';')
    document.body.appendChild(banner)

    const handleMouseOver = (event) => {
      const element = event.target
      if (!(element instanceof HTMLElement) || element === banner) return
      if (activeElement && activeElement !== element) {
        activeElement.style.outline = previousOutline
      }
      activeElement = element
      previousOutline = element.style.outline
      element.style.outline = '2px solid #5be4d0'
    }

    const handleMouseOut = (event) => {
      const element = event.target
      if (!(element instanceof HTMLElement) || element === banner) return
      element.style.outline = previousOutline
    }

    const handleClick = (event) => {
      const element = event.target
      if (!(element instanceof HTMLElement) || element === banner) return
      event.preventDefault()
      event.stopPropagation()
      window.opener?.postMessage(
        {
          type: 'jx-element-picked',
          target: buildFriendlyLabel(element),
          selector: buildSelector(element),
        },
        window.location.origin,
      )
      window.close()
    }

    document.addEventListener('mouseover', handleMouseOver, true)
    document.addEventListener('mouseout', handleMouseOut, true)
    document.addEventListener('click', handleClick, true)

    return () => {
      document.removeEventListener('mouseover', handleMouseOver, true)
      document.removeEventListener('mouseout', handleMouseOut, true)
      document.removeEventListener('click', handleClick, true)
      banner.remove()
      if (activeElement) {
        activeElement.style.outline = previousOutline
      }
    }
  }, [])
}

export default function App() {
  useClientElementPicker()

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/testcases" element={<TestCaseListPage />} />
          <Route path="/testcases/create" element={<TestCasesPage />} />
          <Route path="/executions" element={<ExecutionsPage />} />
          <Route path="/executions/:executionId" element={<ExecutionDetailPage />} />
          <Route path="/ai-agent" element={<AIAgentPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
