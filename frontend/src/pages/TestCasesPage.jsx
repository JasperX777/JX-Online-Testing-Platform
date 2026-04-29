import { useCallback, useEffect, useMemo, useState } from 'react'

import ActionModal from '../components/ActionModal'
import { api } from '../lib/api'

const priorities = ['low', 'medium', 'high']
const statuses = ['draft', 'ready', 'deprecated']
const testTypes = ['functional', 'security', 'performance', 'penetration']

export default function TestCasesPage() {
  const [projects, setProjects] = useState([])
  const [testcases, setTestcases] = useState([])
  const [filters, setFilters] = useState({ projectId: '', category: '', tag: '' })
  const [form, setForm] = useState({
    project: '',
    title: '',
    description: '',
    steps: '',
    expected_result: '',
    category: '',
    tags: '',
    test_type: 'functional',
    pytest_target: '',
    priority: 'medium',
    status: 'draft',
  })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [modal, setModal] = useState({
    open: false,
    mode: null,
    testcase: null,
    values: {
      title: '',
      category: '',
      priority: 'medium',
      status: 'draft',
      pytest_target: '',
    },
  })

  const filterQuery = useMemo(() => {
    const params = new URLSearchParams()
    if (filters.projectId) params.set('project_id', filters.projectId)
    if (filters.category) params.set('category', filters.category)
    if (filters.tag) params.set('tag', filters.tag)
    const query = params.toString()
    return query ? `?${query}` : ''
  }, [filters])

  const loadProjects = useCallback(async () => {
    const data = await api.get('/api/projects/')
    setProjects(data || [])
  }, [])

  const loadTestcases = useCallback(async () => {
    const data = await api.get(`/api/testcases/${filterQuery}`)
    setTestcases(data || [])
  }, [filterQuery])

  useEffect(() => {
    ;(async () => {
      try {
        setError('')
        await Promise.all([loadProjects(), loadTestcases()])
      } catch (err) {
        setError(err.message || 'Failed to load test cases')
      }
    })()
  }, [loadProjects, loadTestcases])

  useEffect(() => {
    ;(async () => {
      try {
        setError('')
        await loadTestcases()
      } catch (err) {
        setError(err.message || 'Failed to filter test cases')
      }
    })()
  }, [loadTestcases])

  const onCreate = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      const payload = {
        ...form,
        project: Number(form.project),
        tags: form.tags
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      }
      if (payload.test_type !== 'functional') {
        payload.pytest_target = ''
      }
      await api.post('/api/testcases/', payload)
      setMessage('Test case created.')
      setForm((prev) => ({
        ...prev,
        title: '',
        description: '',
        steps: '',
        expected_result: '',
        category: '',
        tags: '',
        pytest_target: '',
      }))
      await loadTestcases()
    } catch (err) {
      setError(err.message || 'Create test case failed')
    }
  }

  const openEditModal = (item) => {
    setModal({
      open: true,
      mode: 'edit',
      testcase: item,
      values: {
        title: item.title || '',
        category: item.category || '',
        priority: item.priority || 'medium',
        status: item.status || 'draft',
        pytest_target: item.pytest_target || '',
      },
    })
  }

  const openDeleteModal = (item) => {
    setModal({
      open: true,
      mode: 'delete',
      testcase: item,
      values: {
        title: '',
        category: '',
        priority: 'medium',
        status: 'draft',
        pytest_target: '',
      },
    })
  }

  const closeModal = () => {
    setModal({
      open: false,
      mode: null,
      testcase: null,
      values: {
        title: '',
        category: '',
        priority: 'medium',
        status: 'draft',
        pytest_target: '',
      },
    })
  }

  const onModalFieldChange = (key, value) => {
    setModal((prev) => ({ ...prev, values: { ...prev.values, [key]: value } }))
  }

  const onModalConfirm = async () => {
    if (!modal.testcase) return

    setError('')
    setMessage('')
    try {
      if (modal.mode === 'edit') {
        const payload = {
          title: modal.values.title,
          category: modal.values.category,
          priority: modal.values.priority,
          status: modal.values.status,
          pytest_target: modal.values.pytest_target,
        }
        await api.patch(`/api/testcases/${modal.testcase.id}/`, payload)
        setMessage('Test case updated.')
      } else {
        await api.del(`/api/testcases/${modal.testcase.id}/`)
        setMessage('Test case deleted.')
      }
      closeModal()
      await loadTestcases()
    } catch (err) {
      setError(err.message || 'Test case action failed')
    }
  }

  return (
    <div className="stack-lg">
      <section className="card reveal">
        <div className="card-header">
          <h2>Test Cases</h2>
          <p className="muted-text">Compose and classify test definitions for execution.</p>
        </div>

        <div className="inline-form">
          <select value={filters.projectId} onChange={(event) => setFilters((prev) => ({ ...prev, projectId: event.target.value }))}>
            <option value="">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <input
            placeholder="Category filter"
            value={filters.category}
            onChange={(event) => setFilters((prev) => ({ ...prev, category: event.target.value }))}
          />
          <input
            placeholder="Tag filter"
            value={filters.tag}
            onChange={(event) => setFilters((prev) => ({ ...prev, tag: event.target.value }))}
          />
        </div>
      </section>

      <section className="card reveal">
        <h3>Create Test Case</h3>
        <form className="form-grid two-col" onSubmit={onCreate}>
          <label className="field">
            Project
            <select
              value={form.project}
              onChange={(event) => setForm((prev) => ({ ...prev, project: event.target.value }))}
              required
            >
              <option value="">Select project</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Title
            <input
              value={form.title}
              onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
              required
            />
          </label>
          <label className="field">
            Category
            <input
              value={form.category}
              onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value }))}
            />
          </label>
          <label className="field">
            Tags (comma separated)
            <input
              value={form.tags}
              onChange={(event) => setForm((prev) => ({ ...prev, tags: event.target.value }))}
            />
          </label>
          <label className="field">
            Test Type
            <select
              value={form.test_type}
              onChange={(event) => setForm((prev) => ({ ...prev, test_type: event.target.value }))}
            >
              {testTypes.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Priority
            <select
              value={form.priority}
              onChange={(event) => setForm((prev) => ({ ...prev, priority: event.target.value }))}
            >
              {priorities.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Status
            <select
              value={form.status}
              onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value }))}
            >
              {statuses.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Pytest target
            <input
              value={form.pytest_target}
              onChange={(event) => setForm((prev) => ({ ...prev, pytest_target: event.target.value }))}
              placeholder="required for functional test type"
            />
          </label>
          <label className="field full">
            Description
            <textarea
              value={form.description}
              onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            />
          </label>
          <label className="field full">
            Steps
            <textarea value={form.steps} onChange={(event) => setForm((prev) => ({ ...prev, steps: event.target.value }))} />
          </label>
          <label className="field full">
            Expected Result
            <textarea
              value={form.expected_result}
              onChange={(event) => setForm((prev) => ({ ...prev, expected_result: event.target.value }))}
            />
          </label>
          {message ? <p className="success-text full">{message}</p> : null}
          {error ? <p className="error-text full">{error}</p> : null}
          <button className="button primary full" type="submit">
            Create Test Case
          </button>
        </form>
      </section>

      <section className="card reveal">
        <h3>Visible Test Cases</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Title</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Pytest target</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {testcases.length === 0 ? (
                <tr>
                  <td colSpan={7} className="muted-cell">
                    No test cases found.
                  </td>
                </tr>
              ) : (
                testcases.map((item) => (
                  <tr key={item.id}>
                    <td>{item.project}</td>
                    <td>{item.title}</td>
                    <td>{item.test_type}</td>
                    <td>{item.priority}</td>
                    <td>{item.status}</td>
                    <td className="truncate">{item.pytest_target || '-'}</td>
                    <td>
                      <div className="inline-form">
                        <button className="button ghost" type="button" onClick={() => openEditModal(item)}>
                          Edit
                        </button>
                        <button className="button danger" type="button" onClick={() => openDeleteModal(item)}>
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
        open={modal.open}
        title={
          modal.mode === 'edit'
            ? 'Edit Test Case'
            : 'Delete Test Case'
        }
        description={
          modal.mode === 'edit'
            ? 'Update test case fields.'
            : `This will permanently delete "${modal.testcase?.title || ''}".`
        }
        fields={
          modal.mode === 'edit'
            ? [
                { key: 'title', label: 'Title' },
                { key: 'category', label: 'Category' },
                { key: 'priority', label: 'Priority', type: 'select', options: priorities },
                { key: 'status', label: 'Status', type: 'select', options: statuses },
                { key: 'pytest_target', label: 'Pytest target' },
              ]
            : []
        }
        values={modal.values}
        onChange={onModalFieldChange}
        onCancel={closeModal}
        onConfirm={onModalConfirm}
        confirmText={modal.mode === 'edit' ? 'Save' : 'Delete'}
        danger={modal.mode === 'delete'}
      />
    </div>
  )
}
