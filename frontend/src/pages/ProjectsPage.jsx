import { useEffect, useState } from 'react'

import ActionModal from '../components/ActionModal'
import { api } from '../lib/api'

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [modal, setModal] = useState({
    open: false,
    mode: null,
    project: null,
    values: { name: '', description: '' },
  })

  const loadProjects = async () => {
    const data = await api.get('/api/projects/')
    setProjects(data || [])
  }

  useEffect(() => {
    let canceled = false
    ;(async () => {
      try {
        const data = await api.get('/api/projects/')
        if (!canceled) setProjects(data || [])
      } catch (err) {
        if (!canceled) setError(err.message || 'Failed to load projects')
      }
    })()

    return () => {
      canceled = true
    }
  }, [])

  const onCreateProject = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/api/projects/', { name, description })
      setName('')
      setDescription('')
      setMessage('Project created.')
      await loadProjects()
    } catch (err) {
      setError(err.message || 'Create project failed')
    }
  }

  const openEditModal = (project) => {
    setModal({
      open: true,
      mode: 'edit',
      project,
      values: {
        name: project.name || '',
        description: project.description || '',
      },
    })
  }

  const openDeleteModal = (project) => {
    setModal({
      open: true,
      mode: 'delete',
      project,
      values: { name: '', description: '' },
    })
  }

  const closeModal = () => {
    setModal({ open: false, mode: null, project: null, values: { name: '', description: '' } })
  }

  const onModalFieldChange = (key, value) => {
    setModal((prev) => ({ ...prev, values: { ...prev.values, [key]: value } }))
  }

  const onModalConfirm = async () => {
    if (!modal.project) return

    setError('')
    setMessage('')
    try {
      if (modal.mode === 'edit') {
        await api.put(`/api/projects/${modal.project.id}/`, {
          name: modal.values.name,
          description: modal.values.description,
        })
        setMessage('Project updated.')
      } else {
        await api.del(`/api/projects/${modal.project.id}/`)
        setMessage('Project deleted.')
      }
      closeModal()
      await loadProjects()
    } catch (err) {
      setError(err.message || 'Project action failed')
    }
  }

  return (
    <div className="stack-lg">
      <section className="card reveal">
        <div className="card-header">
          <h2>Projects</h2>
          <p className="muted-text">Create and manage project spaces for execution flows.</p>
        </div>

        <form className="inline-form" onSubmit={onCreateProject}>
          <input placeholder="Project name" value={name} onChange={(event) => setName(event.target.value)} required />
          <input
            placeholder="Description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <button className="button primary" type="submit">
            Create
          </button>
        </form>

        {message ? <p className="success-text">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="card reveal">
        <h3>Project List</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Owner</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {projects.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted-cell">
                    No visible projects.
                  </td>
                </tr>
              ) : (
                projects.map((project) => (
                  <tr key={project.id}>
                    <td>{project.name}</td>
                    <td>{project.description || '-'}</td>
                    <td>{project.owner_username}</td>
                    <td>{new Date(project.created_at).toLocaleString()}</td>
                    <td>
                      <div className="inline-form">
                        <button className="button ghost" type="button" onClick={() => openEditModal(project)}>
                          Edit
                        </button>
                        <button className="button danger" type="button" onClick={() => openDeleteModal(project)}>
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
            ? 'Edit Project'
            : 'Delete Project'
        }
        description={
          modal.mode === 'edit'
            ? 'Update project details.'
            : `This will permanently delete "${modal.project?.name || ''}".`
        }
        fields={
          modal.mode === 'edit'
            ? [
                { key: 'name', label: 'Project name' },
                { key: 'description', label: 'Description' },
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
