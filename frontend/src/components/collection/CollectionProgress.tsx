import type { CollectionJob, CollectionSource, SourceRunResult, SourceRunStatus } from '../../api/types'
import { JOB_STATUS_LABELS, fmtDateTime, fmtDuration, isActive, plural } from './format'

interface Props {
  job: CollectionJob
  sources: CollectionSource[]
  onRetry: () => void
  retrying: boolean
}

const STATUS_ICON: Record<SourceRunStatus, string> = {
  waiting: '○',
  fetching: '⟳',
  completed: '✓',
  partial: '◐',
  failed: '✗',
}

function statusText(r: SourceRunResult, unitLabel: string): string {
  switch (r.status) {
    case 'waiting':
      return 'Waiting'
    case 'fetching':
      if (r.current_unit) {
        return `Fetching ${r.current_unit} (${unitLabel} ${r.units_done + 1} of ${r.units_total})…`
      }
      return r.units_total && r.units_done >= r.units_total ? 'Saving posts…' : 'Starting…'
    case 'completed':
      return `Complete — ${r.fetched} posts`
    case 'partial':
      return `Partly complete — ${r.fetched} posts, some ${plural(unitLabel)} failed`
    case 'failed':
      return r.errors[0] ? `Failed — ${r.errors[0]}` : 'Failed'
  }
}

function sourceProgress(r: SourceRunResult): number {
  if (r.status === 'completed' || r.status === 'failed' || r.status === 'partial') return 1
  if (!r.units_total) return 0
  // Leave the last sliver for the save step after the final unit.
  return Math.min(r.units_done / r.units_total, 0.97)
}

export function CollectionProgress({ job, sources, onRetry, retrying }: Props) {
  const byKey = Object.fromEntries(sources.map((s) => [s.key, s]))
  const label = (key: string) => byKey[key]?.label ?? key
  const running = isActive(job.status)
  const results = job.sources.map((key) => [key, job.source_results[key]] as const)
  const overall = results.reduce((sum, [, r]) => sum + sourceProgress(r), 0) / (results.length || 1)
  const allErrors = results.flatMap(([key, r]) => r.errors.map((e) => `${label(key)}: ${e}`))
  const allWarnings = results.flatMap(([key, r]) => r.warnings.map((w) => `${label(key)}: ${w}`))

  return (
    <section className="dc-card" aria-live="polite">
      <div className="dc-card-head">
        <h3>{running ? 'Collecting posts…' : 'Collection result'}</h3>
        <span className={`dc-status dc-status-${job.status}`}>{JOB_STATUS_LABELS[job.status]}</span>
      </div>

      {running && (
        <div className="dc-progress" role="progressbar" aria-valuenow={Math.round(overall * 100)} aria-valuemin={0} aria-valuemax={100}>
          <div className="dc-progress-fill" style={{ width: `${overall * 100}%` }} />
        </div>
      )}

      <div className="dc-table-wrap">
      <table className="dc-table">
        <thead>
          <tr>
            <th>Source</th>
            <th>Status</th>
            <th className="num">Fetched</th>
            <th className="num">New</th>
            <th className="num">Duplicates</th>
          </tr>
        </thead>
        <tbody>
          {results.map(([key, r]) => (
            <tr key={key}>
              <td>
                <span className={`source-tag source-${key}`}>{label(key)}</span>
              </td>
              <td>
                <span className={`dc-src-status dc-src-${r.status}`}>
                  <span className={r.status === 'fetching' ? 'dc-spin' : undefined} aria-hidden>
                    {STATUS_ICON[r.status]}
                  </span>{' '}
                  {statusText(r, byKey[key]?.unit_label ?? 'unit')}
                </span>
                {r.window_start && (
                  <div className="dc-subtle">
                    Posts from {fmtDateTime(r.window_start)} to {fmtDateTime(r.window_end)}
                  </div>
                )}
              </td>
              <td className="num">{r.status === 'waiting' ? '—' : r.fetched}</td>
              <td className="num">{r.status === 'waiting' ? '—' : r.new}</td>
              <td className="num">{r.status === 'waiting' ? '—' : r.duplicate}</td>
            </tr>
          ))}
        </tbody>
        {!running && (
          <tfoot>
            <tr>
              <td colSpan={2}>Total</td>
              <td className="num">{job.posts_fetched}</td>
              <td className="num">{job.posts_new}</td>
              <td className="num">{job.posts_duplicate}</td>
            </tr>
          </tfoot>
        )}
      </table>
      </div>

      {!running && (
        <p className="dc-subtle">
          Took {fmtDuration(job.duration_s)}.
          {job.posts_skipped > 0 && ` ${job.posts_skipped} post(s) skipped as invalid or conflicting.`}
          {' '}Duplicates are posts already in the database; they were refreshed, not added twice.
        </p>
      )}

      {allErrors.length > 0 && (
        <div className="dc-errors">
          <strong>Errors</strong>
          <ul>
            {allErrors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
          {!running && job.retryable_sources.length > 0 && (
            <button className="dc-btn dc-btn-secondary" onClick={onRetry} disabled={retrying}>
              {retrying ? 'Starting…' : `Retry ${job.retryable_sources.map(label).join(', ')}`}
            </button>
          )}
        </div>
      )}

      {allWarnings.length > 0 && (
        <details className="dc-warnings">
          <summary>{allWarnings.length} note(s)</summary>
          <ul>
            {allWarnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
