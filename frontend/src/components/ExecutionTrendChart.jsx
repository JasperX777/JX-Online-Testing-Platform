export default function ExecutionTrendChart({ analytics }) {
  const trend = analytics?.trend || []
  const trendMax = Math.max(...trend.map((item) => item.total), 1)

  return (
    <section className="card reveal">
      <div className="card-header">
        <div>
          <h3>Seven-day Execution Trend</h3>
          <p className="muted-text">Completed pass rate: {analytics?.pass_rate ?? 0}%</p>
        </div>
      </div>
      <div className="trend-chart" aria-label="Execution totals for the last seven days">
        {trend.map((item) => (
          <div className="trend-column" key={item.date}>
            <div className="trend-bar-track" title={`${item.total} total, ${item.success} successful, ${item.failed} failed`}>
              <div className="trend-bar" style={{ height: `${Math.max((item.total / trendMax) * 100, item.total ? 8 : 0)}%` }} />
            </div>
            <strong>{item.total}</strong>
            <span>{item.date.slice(5)}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
