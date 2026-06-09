import StatusPill from './StatusPill'

export default function ScheduleTable({ schedules, onCancel }) {
  return (
    <section className="card reveal">
      <h3>Scheduled Executions</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Project</th>
              <th>Test Case</th>
              <th>Scheduled For</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {schedules.length === 0 ? (
              <tr>
                <td colSpan={5} className="muted-cell">No scheduled executions.</td>
              </tr>
            ) : schedules.map((schedule) => (
              <tr key={schedule.id}>
                <td>{schedule.project_name}</td>
                <td>{schedule.testcase_title}</td>
                <td>{new Date(schedule.scheduled_for).toLocaleString()}</td>
                <td><StatusPill status={schedule.status} /></td>
                <td>
                  {schedule.status === 'pending' ? (
                    <button className="button danger" type="button" onClick={() => onCancel(schedule.id)}>
                      Cancel
                    </button>
                  ) : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
