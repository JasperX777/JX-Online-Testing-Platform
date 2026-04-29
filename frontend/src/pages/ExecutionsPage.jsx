import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import ActionModal from '../components/ActionModal'
import StatusPill from '../components/StatusPill'
import { api } from '../lib/api'

export default function ExecutionsPage() {
  const [projects, setProjects] = useState([])
  const [testcases, setTestcases] = useState([])
  const [executions, setExecutions] = useState([])
  const [projectCaseCounts, setProjectCaseCounts] = useState({})
  const [projectId, setProjectId] = useState('')
  const [testcaseId, setTestcaseId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)

  const filteredTestcases = useMemo(() => testcases, [testcases])

  const loadData = async () => {
    const [projectData, executionData, allTestcasesData] = await Promise.all([
      api.get('/api/projects/'),
      api.get('/api/executions/'),
      api.get('/api/testcases/'),
    ])
    setProjects(projectData || [])
    setExecutions(executionData || [])
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

  const runExecution = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/api/executions/run/', {
        project: Number(projectId),
        testcase: Number(testcaseId),
      })
      setMessage('Execution created.')
      await loadData()
      await loadTestcasesForProject(projectId)
    } catch (err) {
      setError(err.message || 'Execution request failed')
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
          <p className="muted-text">Trigger runs and manage execution history from one place.</p>
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
        </form>

        {message ? <p className="success-text">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
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
                <th>Exit</th>
                <th>Summary</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {executions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="muted-cell">
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
                    <td>{execution.exit_code ?? '-'}</td>
                    <td className="truncate">{execution.result_summary || '-'}</td>
                    <td className="action-row">
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
