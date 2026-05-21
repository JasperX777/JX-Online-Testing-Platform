import { useCallback, useEffect, useMemo, useState } from 'react'

import ActionModal from '../components/ActionModal'
import ElementPickerPanel from '../components/ElementPickerPanel'
import { api } from '../lib/api'

const priorities = ['low', 'medium', 'high', 'critical']
const statuses = ['draft', 'ready', 'deprecated']
const stepActions = [
  { value: 'launch_browser', label: 'Launch Browser' },
  { value: 'open_page', label: 'Open Page' },
  { value: 'click_button', label: 'Click Button' },
  { value: 'input_text', label: 'Input Text' },
  { value: 'press_key', label: 'Press Key' },
  { value: 'verify_element', label: 'Verify Element' },
]

function createEmptyStep() {
  return {
    step_title: '',
    action: '',
    target: '',
    locator_type: 'css',
    selector: '',
    value: '',
    note: '',
  }
}

function buildDescription(step) {
  switch (step.action) {
    case 'launch_browser':
      return `Launch the ${step.value || 'selected'} browser.`
    case 'open_page':
      return `Open ${step.value || 'the target page'} in the browser.`
    case 'input_text':
      return `Type ${step.value || 'the value'} into ${step.target || step.step_title || 'the selected field'}.`
    case 'click_button':
      return `Click ${step.target || step.step_title || 'the selected button'}.`
    case 'press_key':
      return `Press the ${step.value || 'configured'} key.`
    case 'verify_element':
      return `Verify that ${step.target || step.step_title || 'the selected element'} is visible.`
    default:
      return step.step_title || 'Configure this step.'
  }
}

function normalizeSteps(steps) {
  return steps.map((step, index) => ({
    step_no: index + 1,
    step_title: step.step_title.trim(),
    description: buildDescription(step),
    action: step.action,
    target: step.target.trim() || step.step_title.trim(),
    locator_type: 'css',
    selector: step.selector.trim(),
    value: step.value,
    note: step.note,
  }))
}

export default function TestCaseListPage() {
  const [projects, setProjects] = useState([])
  const [testcases, setTestcases] = useState([])
  const [filters, setFilters] = useState({ projectId: '', category: '', tag: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [modal, setModal] = useState({
    open: false,
    mode: null,
    testcase: null,
    tab: 'info',
    pickerStepIndex: null,
    values: {
      title: '',
      module: '',
      scenario: '',
      category: '',
      priority: 'medium',
      status: 'draft',
      description: '',
      tags: '',
    },
    steps: [createEmptyStep()],
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

  const openEditModal = (item) => {
    setModal({
      open: true,
      mode: 'edit',
      testcase: item,
      tab: 'info',
      pickerStepIndex: null,
      values: {
        title: item.title || '',
        module: item.module || '',
        scenario: item.scenario || '',
        category: item.category || '',
        priority: item.priority || 'medium',
        status: item.status || 'draft',
        description: item.description || '',
        tags: (item.tags || []).join(', '),
      },
      steps: (item.steps_json || []).map((step) => ({
        step_title: step.step_title || '',
        action: step.action || '',
        target: step.target || '',
        locator_type: step.locator_type || 'css',
        selector: step.selector || '',
        value: step.value || '',
        note: step.note || '',
      })),
    })
  }

  const openDeleteModal = (item) => {
    setModal({
      open: true,
      mode: 'delete',
      testcase: item,
      tab: 'info',
      pickerStepIndex: null,
      values: {
        title: '',
        module: '',
        scenario: '',
        category: '',
        priority: 'medium',
        status: 'draft',
        description: '',
        tags: '',
      },
      steps: [createEmptyStep()],
    })
  }

  const closeModal = () => {
    setModal({
      open: false,
      mode: null,
      testcase: null,
      tab: 'info',
      pickerStepIndex: null,
      values: {
        title: '',
        module: '',
        scenario: '',
        category: '',
        priority: 'medium',
        status: 'draft',
        description: '',
        tags: '',
      },
      steps: [createEmptyStep()],
    })
  }

  const onModalFieldChange = (key, value) => {
    setModal((prev) => ({ ...prev, values: { ...prev.values, [key]: value } }))
  }

  const onModalStepChange = (index, key, value) => {
    setModal((prev) => ({
      ...prev,
      steps: prev.steps.map((step, stepIndex) => (stepIndex === index ? { ...step, [key]: value } : step)),
    }))
  }

  const addModalStep = () => {
    setModal((prev) => ({ ...prev, steps: [...prev.steps, createEmptyStep()] }))
  }

  const removeModalStep = (index) => {
    setModal((prev) => {
      if (prev.steps.length === 1) return prev
      return { ...prev, steps: prev.steps.filter((_, stepIndex) => stepIndex !== index) }
    })
  }

  const moveModalStep = (index, direction) => {
    setModal((prev) => {
      const nextIndex = index + direction
      if (nextIndex < 0 || nextIndex >= prev.steps.length) return prev
      const nextSteps = [...prev.steps]
      const [step] = nextSteps.splice(index, 1)
      nextSteps.splice(nextIndex, 0, step)
      return { ...prev, steps: nextSteps }
    })
  }

  const modalSuggestedPreviewUrl = useMemo(
    () => modal.steps.find((step) => step.action === 'open_page' && step.value.trim())?.value.trim() || '',
    [modal.steps],
  )
  const modalSuggestedPickerBrowser = useMemo(
    () => modal.steps.find((step) => step.action === 'launch_browser' && step.value.trim())?.value.trim() || 'chromium',
    [modal.steps],
  )

  const onModalConfirm = async () => {
    if (!modal.testcase) return

    setError('')
    setMessage('')
    try {
      if (modal.mode === 'edit') {
        const payload = {
          title: modal.values.title,
          module: modal.values.module,
          scenario: modal.values.scenario,
          category: modal.values.category,
          priority: modal.values.priority,
          status: modal.values.status,
          description: modal.values.description,
          tags: modal.values.tags
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          steps_json: normalizeSteps(modal.steps),
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
          <h2>Test Case List</h2>
          <p className="muted-text">Browse, filter, and manage your saved automated test cases.</p>
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

        {message ? <p className="success-text">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="card reveal">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Title</th>
                <th>Module</th>
                <th>Scenario</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Steps</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {testcases.length === 0 ? (
                <tr>
                  <td colSpan={8} className="muted-cell">
                    No test cases found.
                  </td>
                </tr>
              ) : (
                testcases.map((item) => (
                  <tr key={item.id}>
                    <td>{item.project}</td>
                    <td>{item.title}</td>
                    <td>{item.module || '-'}</td>
                    <td>{item.scenario || '-'}</td>
                    <td>{item.priority}</td>
                    <td>{item.status}</td>
                    <td>{item.steps_json?.length || 0}</td>
                    <td>
                      <div className="action-row">
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
        open={modal.open && modal.mode === 'delete'}
        title="Delete Test Case"
        description={`This will permanently delete "${modal.testcase?.title || ''}".`}
        onCancel={closeModal}
        onConfirm={onModalConfirm}
        confirmText="Delete"
        danger
      />

      {modal.open && modal.mode === 'edit' ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Edit Test Case">
          <div className="modal-card modal-card-lg">
            <div className="modal-card-header">
              <div>
                <h3>Edit Test Case</h3>
                <p className="muted-text">Switch between test case information and steps without leaving the list view.</p>
              </div>
            </div>

            <div className="mode-switch">
              <button
                className={`mode-tab ${modal.tab === 'info' ? 'active' : ''}`}
                type="button"
                onClick={() => setModal((prev) => ({ ...prev, tab: 'info' }))}
              >
                Test Case Info
              </button>
              <button
                className={`mode-tab ${modal.tab === 'steps' ? 'active' : ''}`}
                type="button"
                onClick={() => setModal((prev) => ({ ...prev, tab: 'steps' }))}
              >
                Test Case Steps
              </button>
            </div>

            <div className="modal-scroll">
              {modal.tab === 'info' ? (
                <div className="form-grid two-col">
                  <label className="field">
                    Title
                    <input value={modal.values.title} onChange={(event) => onModalFieldChange('title', event.target.value)} />
                  </label>
                  <label className="field">
                    Module
                    <input value={modal.values.module} onChange={(event) => onModalFieldChange('module', event.target.value)} />
                  </label>
                  <label className="field">
                    Scenario
                    <input value={modal.values.scenario} onChange={(event) => onModalFieldChange('scenario', event.target.value)} />
                  </label>
                  <label className="field">
                    Category
                    <input value={modal.values.category} onChange={(event) => onModalFieldChange('category', event.target.value)} />
                  </label>
                  <label className="field">
                    Priority
                    <select value={modal.values.priority} onChange={(event) => onModalFieldChange('priority', event.target.value)}>
                      {priorities.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Status
                    <select value={modal.values.status} onChange={(event) => onModalFieldChange('status', event.target.value)}>
                      {statuses.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field full">
                    Description
                    <textarea value={modal.values.description} onChange={(event) => onModalFieldChange('description', event.target.value)} />
                  </label>
                  <label className="field full">
                    Tags
                    <input value={modal.values.tags} onChange={(event) => onModalFieldChange('tags', event.target.value)} />
                  </label>
                </div>
              ) : (
                <div className="stack-md">
                  {modal.steps.map((step, index) => {
                    const isLastStep = index === modal.steps.length - 1
                    const actionNeedsTarget = !['launch_browser', 'press_key'].includes(step.action)

                    return (
                      <div key={index} className="card">
                        <div className="card-header">
                          <strong>Step {index + 1}</strong>
                          <div className="inline-form">
                            <button className="button ghost" type="button" onClick={() => moveModalStep(index, -1)}>
                              Up
                            </button>
                            <button className="button ghost" type="button" onClick={() => moveModalStep(index, 1)}>
                              Down
                            </button>
                            <button className="button danger" type="button" onClick={() => removeModalStep(index)}>
                              Remove
                            </button>
                          </div>
                        </div>

                        <div className="form-grid two-col">
                          <label className="field">
                            Step Title
                            <input
                              value={step.step_title}
                              onChange={(event) => onModalStepChange(index, 'step_title', event.target.value)}
                            />
                          </label>
                          <label className="field">
                            Action
                            <select value={step.action} onChange={(event) => onModalStepChange(index, 'action', event.target.value)}>
                              <option value="">Select action</option>
                              {stepActions.map((item) => (
                                <option key={item.value} value={item.value}>
                                  {item.label}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="field">
                            Value
                            <input
                              value={step.value}
                              onChange={(event) => onModalStepChange(index, 'value', event.target.value)}
                            />
                          </label>
                          <label className="field">
                            Note
                            <input
                              value={step.note}
                              onChange={(event) => onModalStepChange(index, 'note', event.target.value)}
                            />
                          </label>
                          {actionNeedsTarget ? (
                            <>
                              <label className="field">
                                Picked Target
                                <input
                                  value={step.target}
                                  onChange={(event) => onModalStepChange(index, 'target', event.target.value)}
                                />
                              </label>
                              <label className="field">
                                CSS Selector
                                <input
                                  value={step.selector}
                                  onChange={(event) => onModalStepChange(index, 'selector', event.target.value)}
                                />
                              </label>
                              <div className="field full">
                                <div className="inline-form">
                                  <button
                                    className="button ghost"
                                    type="button"
                                    onClick={() => setModal((prev) => ({ ...prev, pickerStepIndex: index }))}
                                  >
                                    Pick Element For This Step
                                  </button>
                                </div>
                              </div>
                            </>
                          ) : null}
                        </div>

                        {isLastStep ? (
                          <div className="inline-form" style={{ justifyContent: 'flex-end' }}>
                            <button className="button ghost" type="button" onClick={addModalStep}>
                              Add Step
                            </button>
                          </div>
                        ) : null}
                      </div>
                    )
                  })}

                  <ElementPickerPanel
                    activeStepIndex={modal.pickerStepIndex}
                    activeStepTitle={modal.pickerStepIndex !== null ? modal.steps[modal.pickerStepIndex]?.step_title : ''}
                    suggestedUrl={modalSuggestedPreviewUrl}
                    suggestedBrowser={modalSuggestedPickerBrowser}
                    onPick={({ target, selector }) => {
                      if (modal.pickerStepIndex === null) return
                      setModal((prev) => ({
                        ...prev,
                        steps: prev.steps.map((step, index) =>
                          index === prev.pickerStepIndex ? { ...step, target, selector } : step,
                        ),
                      }))
                    }}
                  />
                </div>
              )}
            </div>

            <div className="inline-form">
              <button className="button ghost" type="button" onClick={closeModal}>
                Cancel
              </button>
              <button className="button primary" type="button" onClick={onModalConfirm}>
                Save
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
