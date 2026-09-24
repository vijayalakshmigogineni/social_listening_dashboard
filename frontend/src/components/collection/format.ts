import type { CollectionJob, CollectionMode, JobStatus } from '../../api/types'

export const MODE_LABELS: Record<CollectionMode, string> = {
  since_last_sweep: 'Since last sweep',
  custom_range: 'Custom date range',
  latest_n: 'Latest posts',
}

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  completed_with_errors: 'Completed with errors',
  failed: 'Failed',
  interrupted: 'Interrupted',
}

export function isActive(status: JobStatus | undefined): boolean {
  return status === 'queued' || status === 'running'
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function fmtDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 60) return `${Math.round(seconds)} s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m} min ${s} s`
}

/** The span of post dates a job asked for, in words. */
export function describeRange(job: CollectionJob): string {
  if (job.mode === 'latest_n') return `Newest ${job.post_limit} per source`
  if (job.mode === 'custom_range') {
    return `${fmtDateTime(job.start_date)} → ${fmtDateTime(job.end_date)} (max ${job.post_limit}/source)`
  }
  const starts = Object.values(job.source_results)
    .map((r) => r.window_start)
    .filter((s): s is string => !!s)
    .sort()
  const end = Object.values(job.source_results).find((r) => r.window_end)?.window_end
  if (!starts.length) return 'From each source’s last sweep'
  return `${fmtDateTime(starts[0])} → ${fmtDateTime(end)}`
}

/** `datetime-local` input value for a Date, in the browser's time zone. */
export function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** "subreddit" -> "subreddits", "query family" -> "query families". */
export function plural(word: string, n = 2): string {
  if (n === 1) return word
  return word.endsWith('y') ? `${word.slice(0, -1)}ies` : `${word}s`
}
