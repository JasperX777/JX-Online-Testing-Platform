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

export default function App() {
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
