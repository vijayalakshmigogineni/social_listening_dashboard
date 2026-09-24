import type { AnalysisJob, CollectionJob, CollectionSource } from '../../api/types'
import { JOB_STATUS_LABELS, MODE_LABELS, describeRange, fmtDateTime } from './format'

interface Props {
  jobs: CollectionJob[]
  sources: CollectionSource[]
  lastAnalysis: AnalysisJob | null
}

export function CollectionHistory({ jobs, sources, lastAnalysis }: Props) {
  const label = (key: string) => sources.find((s) => s.key === key)?.label ?? key

  return (
    <section className="dc-card">
      <div className="dc-card-head">
        <h3>Collection history</h3>
        {lastAnalysis?.completed_at && (
          <span className="dc-subtle">
            Last analysis: {fmtDateTime(lastAnalysis.completed_at)} ({lastAnalysis.processed_posts}{' '}
            posts)
          </span>
        )}
      </div>
      {jobs.length === 0 ? (
        <p className="dc-subtle">No collections have been run from the dashboard yet.</p>
      ) : (
        <div className="dc-table-wrap">
          <table className="dc-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Mode</th>
                <th>Sources</th>
                <th>Date range</th>
                <th className="num">Fetched</th>
                <th className="num">New</th>
                <th className="num">Dupes</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{fmtDateTime(j.started_at ?? j.created_at)}</td>
                  <td>
                    {MODE_LABELS[j.mode]}
                    {j.retry_of && <div className="dc-subtle">retry of #{j.retry_of}</div>}
                  </td>
                  <td>{j.sources.map(label).join(', ')}</td>
                  <td>{describeRange(j)}</td>
                  <td className="num">{j.posts_fetched}</td>
                  <td className="num">{j.posts_new}</td>
                  <td className="num">{j.posts_duplicate}</td>
                  <td>
                    <span className={`dc-status dc-status-${j.status}`}>{JOB_STATUS_LABELS[j.status]}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
