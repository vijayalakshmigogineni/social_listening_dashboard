import { Link } from 'react-router-dom'
import { SCORING_VERSION } from '../../api/client'
import type { AnalysisJob } from '../../api/types'
import { SCORE_TIERS, scoreTier } from '../scoreTiers'
import { JOB_STATUS_LABELS, fmtDuration, isActive } from './format'

interface Props {
  job: AnalysisJob | null
  pending: number | null
  canStart: boolean
  starting: boolean
  onStart: () => void
}

export function AnalysisPanel({ job, pending, canStart, starting, onStart }: Props) {
  const running = isActive(job?.status)

  return (
    <section className="dc-card">
      <div className="dc-card-head">
        <h3>SLD Analysis</h3>
        {job && <span className={`dc-status dc-status-${job.status}`}>{JOB_STATUS_LABELS[job.status]}</span>}
      </div>

      {!running && (
        <div className="dc-analysis-start">
          <p>
            {pending === null
              ? 'Checking for posts waiting for analysis…'
              : pending === 0
                ? 'Every stored post has already been analyzed.'
                : `${pending} post${pending === 1 ? ' is' : 's are'} waiting for analysis.`}
          </p>
          <button className="dc-btn" onClick={onStart} disabled={!canStart || starting || !pending}>
            {starting ? 'Starting…' : 'Run SLD Analysis'}
          </button>
        </div>
      )}

      {job && running && <AnalysisProgress job={job} />}
      {job && !running && <AnalysisResult job={job} />}
    </section>
  )
}

function AnalysisProgress({ job }: { job: AnalysisJob }) {
  const done = job.processed_posts + job.failed_posts
  const pct = job.total_posts ? (done / job.total_posts) * 100 : 0
  return (
    <div aria-live="polite">
      <div className="dc-progress" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
        <div className="dc-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="dc-counts">
        <span>
          <strong>{done}</strong> of {job.total_posts} posts
        </span>
        <span>
          <strong>{job.processed_posts}</strong> analyzed
        </span>
        <span className={job.failed_posts ? 'dc-bad' : undefined}>
          <strong>{job.failed_posts}</strong> failed
        </span>
      </div>
      <ol className="dc-stages">
        {job.stages.map((name, i) => (
          <li key={name} className={job.current_stage_number === i + 1 ? 'dc-stage-current' : undefined}>
            Step {i + 1}/{job.stages.length} — {name}
          </li>
        ))}
      </ol>
      <p className="dc-subtle">
        Each post goes through all six steps in turn; the highlighted step is where the current post
        is. The first run after a server start loads the language model and can pause for a minute.
      </p>
    </div>
  )
}

function AnalysisResult({ job }: { job: AnalysisJob }) {
  const scores = job.scores[SCORING_VERSION] ?? []
  const tiers = Object.fromEntries(SCORE_TIERS.map((t) => [t, 0])) as Record<string, number>
  scores.forEach((s) => (tiers[scoreTier(s)] += 1))

  if (job.total_posts === 0 && job.status === 'completed') {
    return <p className="dc-subtle">Last run found nothing new to analyze.</p>
  }

  return (
    <div className="dc-analysis-result">
      <p className="dc-result-headline">
        {job.status === 'interrupted' ? 'Analysis interrupted' : 'Analysis complete'} —{' '}
        {job.processed_posts} post{job.processed_posts === 1 ? '' : 's'} analyzed
        {job.failed_posts > 0 && `, ${job.failed_posts} failed`} ({fmtDuration(job.duration_s)})
      </p>
      <div className="dc-tiers">
        {SCORE_TIERS.map((t) => (
          <div key={t} className={`dc-tier dc-tier-${t.toLowerCase()}`}>
            <div className="stat-value">{tiers[t]}</div>
            <div className="stat-label">{t}</div>
          </div>
        ))}
      </div>
      {job.errors.length > 0 && (
        <details className="dc-errors" open={job.processed_posts === 0}>
          <summary>
            {job.errors.length} error{job.errors.length === 1 ? '' : 's'} — failed posts stay
            unanalyzed and are retried on the next run
          </summary>
          <ul>
            {job.errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </details>
      )}
      <Link className="dc-btn" to="/">
        View Dashboard
      </Link>
    </div>
  )
}
