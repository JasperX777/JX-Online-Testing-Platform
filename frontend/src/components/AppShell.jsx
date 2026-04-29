import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/projects', label: 'Projects' },
  { to: '/testcases', label: 'Test Cases' },
  { to: '/executions', label: 'Executions' },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const onLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="shell">
      <aside className="shell-sidebar">
        <div className="brand-block">
          <p className="brand-eyebrow">JX Platform</p>
          <h1>Test Control</h1>
        </div>
        <nav className="side-nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <section className="shell-main">
        <header className="shell-header">
          <div>
            <p className="header-label">Signed in as</p>
            <p className="header-user">{user?.username}</p>
          </div>
          <button className="button ghost" onClick={onLogout} type="button">
            Log out
          </button>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </section>
    </div>
  )
}
