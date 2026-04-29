export default function ActionModal({
  open,
  title,
  description,
  fields = [],
  values = {},
  confirmText = 'Confirm',
  danger = false,
  onChange,
  onCancel,
  onConfirm,
}) {
  if (!open) return null

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal-card">
        <h3>{title}</h3>
        {description ? <p className="muted-text">{description}</p> : null}

        {fields.length > 0 ? (
          <div className="form-grid">
            {fields.map((field) => (
              <label key={field.key} className="field">
                {field.label}
                {field.type === 'select' ? (
                  <select
                    value={values[field.key] ?? ''}
                    onChange={(event) => onChange(field.key, event.target.value)}
                  >
                    {(field.options || []).map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={values[field.key] ?? ''}
                    onChange={(event) => onChange(field.key, event.target.value)}
                  />
                )}
              </label>
            ))}
          </div>
        ) : null}

        <div className="inline-form">
          <button className="button ghost" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button className={`button ${danger ? 'danger' : 'primary'}`} type="button" onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
