export default function StatusPill({ status }) {
  const normalized = (status || 'unknown').toLowerCase()
  return <span className={`status-pill status-${normalized}`}>{normalized}</span>
}
