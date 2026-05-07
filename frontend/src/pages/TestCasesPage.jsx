import { useCallback, useEffect, useMemo, useState } from 'react'

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

function formatStep(step) {
  const title = step.step_title ? `${step.step_title}: ` : ''
  return `${title}${buildDescription(step)}`
}

export default function TestCasesPage() {
  const [projects, setProjects] = useState([])
  const [form, setForm] = useState({
    project: '',
    title: '',
    module: '',
    scenario: '',
    description: '',
    category: '',
    tags: '',
    priority: 'medium',
    status: 'draft',
  })
  const [steps, setSteps] = useState([createEmptyStep()])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [pickerStepIndex, setPickerStepIndex] = useState(null)

  const loadProjects = useCallback(async () => {
    const data = await api.get('/api/projects/')
    setProjects(data || [])
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        setError('')
        await loadProjects()
      } catch (err) {
        setError(err.message || 'Failed to load projects')
      }
    })()
  }, [loadProjects])

  const previewTitle = useMemo(() => {
    if (form.title.trim()) return form.title.trim()
    if (form.module.trim() && form.scenario.trim()) return `${form.module.trim()} - ${form.scenario.trim()}`
    if (form.scenario.trim()) return form.scenario.trim()
    return 'Untitled Test Case'
  }, [form.title, form.module, form.scenario])

  const suggestedPreviewUrl = useMemo(
    () => steps.find((step) => step.action === 'open_page' && step.value.trim())?.value.trim() || '',
    [steps],
  )
  const suggestedPickerBrowser = useMemo(
    () => steps.find((step) => step.action === 'launch_browser' && step.value.trim())?.value.trim() || 'chromium',
    [steps],
  )

  const updateStep = (index, key, value) => {
    setSteps((prev) => prev.map((step, stepIndex) => (stepIndex === index ? { ...step, [key]: value } : step)))
  }

  const addStep = () => setSteps((prev) => [...prev, createEmptyStep()])

  const removeStep = (index) => {
    setSteps((prev) => {
      if (prev.length === 1) return prev
      return prev.filter((_, stepIndex) => stepIndex !== index)
    })
  }

  const moveStep = (index, direction) => {
    setSteps((prev) => {
      const nextIndex = index + direction
      if (nextIndex < 0 || nextIndex >= prev.length) return prev
      const next = [...prev]
      const [step] = next.splice(index, 1)
      next.splice(nextIndex, 0, step)
      return next
    })
  }

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
        steps_json: normalizeSteps(steps),
      }
      await api.post('/api/testcases/', payload)
      setMessage('Test case created.')
      setForm({
        project: form.project,
        title: '',
        module: '',
        scenario: '',
        description: '',
        category: '',
        tags: '',
        priority: 'medium',
        status: 'draft',
      })
      setSteps([createEmptyStep()])
      setPickerStepIndex(null)
    } catch (err) {
      setError(err.message || 'Create test case failed')
    }
  }

  return (
    <div className="stack-lg">
      <section className="card reveal">
        <div className="card-header">
          <h2>Create Test Case</h2>
          <p className="muted-text">Author a new automated test case with the smallest useful set of inputs.</p>
        </div>

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
            <input value={form.title} onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))} />
          </label>
          <label className="field">
            Module
            <input
              value={form.module}
              onChange={(event) => setForm((prev) => ({ ...prev, module: event.target.value }))}
            />
          </label>
          <label className="field">
            Scenario
            <input
              value={form.scenario}
              onChange={(event) => setForm((prev) => ({ ...prev, scenario: event.target.value }))}
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
            <input value={form.tags} onChange={(event) => setForm((prev) => ({ ...prev, tags: event.target.value }))} />
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
            <select value={form.status} onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value }))}>
              {statuses.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field full">
            Description
            <textarea
              value={form.description}
              onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
              placeholder="Add setup notes, scope, or supporting details."
            />
          </label>

          <div className="field full">
            <div className="card-header">
              <div>
                <h4>Step Builder</h4>
                <p className="muted-text">Focus on step name, action, and value. Add automation details only when needed.</p>
              </div>
            </div>

            <div className="stack-md">
              {steps.map((step, index) => {
                const isLastStep = index === steps.length - 1
                const actionNeedsTarget = !['launch_browser', 'press_key'].includes(step.action)

                return (
                  <div key={index} className="card">
                    <div className="card-header">
                      <strong>Step {index + 1}</strong>
                      <div className="inline-form">
                        <button className="button ghost" type="button" onClick={() => moveStep(index, -1)}>
                          Up
                        </button>
                        <button className="button ghost" type="button" onClick={() => moveStep(index, 1)}>
                          Down
                        </button>
                        <button className="button danger" type="button" onClick={() => removeStep(index)}>
                          Remove
                        </button>
                      </div>
                    </div>

                    <div className="form-grid two-col">
                      <label className="field">
                        Step Title
                        <input
                          value={step.step_title}
                          onChange={(event) => updateStep(index, 'step_title', event.target.value)}
                          placeholder="Enter keyword"
                          required
                        />
                      </label>
                      <label className="field">
                        Action
                        <select value={step.action} onChange={(event) => updateStep(index, 'action', event.target.value)} required>
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
                          onChange={(event) => updateStep(index, 'value', event.target.value)}
                          placeholder={
                            step.action === 'launch_browser'
                              ? 'chromium, chrome, firefox, safari'
                              : step.action === 'open_page'
                                ? 'https://example.com'
                                : step.action === 'input_text'
                                  ? 'Text to type'
                                  : step.action === 'press_key'
                                    ? 'Enter'
                                    : ''
                          }
                        />
                      </label>
                      {actionNeedsTarget ? (
                        <div className="field full">
                          <div className="inline-form">
                            <span className="muted-text">Use the button below or the picker panel to capture a target and selector from a real browser window.</span>
                          </div>
                        </div>
                      ) : null}
                      <details className="field full">
                        <summary>Advanced Automation Details</summary>
                        <div className="form-grid two-col">
                          {actionNeedsTarget ? (
                            <>
                              <label className="field">
                                Picked Target
                                <input
                                  value={step.target}
                                  onChange={(event) => updateStep(index, 'target', event.target.value)}
                                  placeholder="Element name users can understand"
                                />
                              </label>
                              <label className="field">
                                CSS Selector
                                <input
                                  value={step.selector}
                                  onChange={(event) => updateStep(index, 'selector', event.target.value)}
                                  placeholder={step.action === 'open_page' ? 'Optional for open_page' : 'Temporary manual fallback until picker is ready'}
                                />
                              </label>
                              <label className="field">
                                Note
                                <input value={step.note} onChange={(event) => updateStep(index, 'note', event.target.value)} />
                              </label>
                            </>
                          ) : (
                            <p className="muted-text">No extra automation fields are required for this action.</p>
                          )}
                        </div>
                      </details>
                    </div>

                        {isLastStep ? (
                          <div className="inline-form" style={{ justifyContent: 'flex-end' }}>
                            <button className="button ghost" type="button" onClick={addStep}>
                              Add Step
                            </button>
                          </div>
                        ) : null}
                        {actionNeedsTarget ? (
                          <div className="inline-form" style={{ justifyContent: 'flex-start' }}>
                            <button className="button ghost" type="button" onClick={() => setPickerStepIndex(index)}>
                              Pick Element For This Step
                            </button>
                          </div>
                        ) : null}
                  </div>
                )
              })}
            </div>
          </div>

          <div className="field full">
            <ElementPickerPanel
              activeStepIndex={pickerStepIndex}
              activeStepTitle={pickerStepIndex !== null ? steps[pickerStepIndex]?.step_title : ''}
              suggestedUrl={suggestedPreviewUrl}
              suggestedBrowser={suggestedPickerBrowser}
              onPick={({ target, selector }) => {
                if (pickerStepIndex === null) return
                setSteps((prev) =>
                  prev.map((step, index) =>
                    index === pickerStepIndex
                      ? { ...step, target, selector }
                      : step,
                  ),
                )
              }}
            />
          </div>

          <div className="field full">
            <h4>Preview</h4>
            <p className="muted-text">Title: {previewTitle}</p>
            <div className="stack-sm">
              {normalizeSteps(steps).map((step) => (
                <article key={step.step_no} className="card">
                  <strong>
                    Step {step.step_no}: {step.step_title || 'Untitled step'}
                  </strong>
                  <p>{formatStep(step)}</p>
                  <p className="muted-text">Action: {stepActions.find((item) => item.value === step.action)?.label || step.action || '-'}</p>
                  {['launch_browser', 'press_key'].includes(step.action) ? null : <p className="muted-text">Target: {step.target || step.step_title || '-'}</p>}
                  {step.value ? <p className="muted-text">Value: {step.value}</p> : null}
                </article>
              ))}
            </div>
          </div>

          {message ? <p className="success-text full">{message}</p> : null}
          {error ? <p className="error-text full">{error}</p> : null}
          <button className="button primary full" type="submit">
            Create Test Case
          </button>
        </form>
      </section>
    </div>
  )
}
