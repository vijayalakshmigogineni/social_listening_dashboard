import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type {
  AnalysisJob,
  CollectionJob,
  CollectionJobRequest,
  CollectionMode,
  CollectionSource,
  SourceStatsResponse,
} from '../api/types'
import { AnalysisPanel } from '../components/collection/AnalysisPanel'
import { CollectionHistory } from '../components/collection/CollectionHistory'
import { CollectionProgress } from '../components/collection/CollectionProgress'
import { CollectionStepper, type StepperState } from '../components/collection/CollectionStepper'
import { SourceCard } from '../components/collection/SourceCard'
import { SourceEditor } from '../components/collection/SourceEditor'
import { MODE_LABELS, isActive, toLocalInput } from '../components/collection/format'

const POLL_MS = 1500 // while a job this page is showing runs
const LIVE_MS = 5000 // otherwise: sources, stats, history, pending, jobs started elsewhere

const MODE_HELP: Record<CollectionMode, string> = {
  since_last_sweep:
    'Everything posted since each source was last swept, up to now. The time range is worked out for you.',
  custom_range: 'Posts made between two dates, up to a number of posts per source.',
  latest_n: 'The newest posts from each source, whenever they were made.',
}

/** Re-run `tick` every `ms` while `active` and the tab is visible. */
function usePolling(active: boolean, ms: number, tick: () => void) {
  useEffect(() => {
    if (!active) return
    const id = setInterval(() => {
      if (!document.hidden) tick()
    }, ms)
    return () => clearInterval(id)
  }, [active, ms, tick])
}

/** "just now" / "12 s ago" -- re-rendered every second. */
function useAgo(since: number | null): string {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  if (since === null) return '—'
  const s = Math.max(0, Math.round((now - since) / 1000))
  return s < 3 ? 'just now' : `${s} s ago`
}

function stepperState(
  collection: CollectionJob | null,
  analysis: AnalysisJob | null,
  pending: number | null,
): StepperState {
  if (isActive(collection?.status)) return { choose: 'done', fetch: 'active', analyze: 'todo', dashboard: 'todo' }
  if (isActive(analysis?.status)) return { choose: 'done', fetch: 'done', analyze: 'active', dashboard: 'todo' }
  const fetched = collection !== null && !isActive(collection.status)
  if (fetched && (pending ?? 0) > 0) return { choose: 'done', fetch: 'done', analyze: 'active', dashboard: 'todo' }
  if (fetched && analysis && !isActive(analysis.status) && (pending ?? 0) === 0) {
    return { choose: 'done', fetch: 'done', analyze: 'done', dashboard: 'done' }
  }
  return { choose: 'active', fetch: 'todo', analyze: 'todo', dashboard: 'todo' }
}

export function DataCollection() {
  const [sources, setSources] = useState<CollectionSource[]>([])
  const [stats, setStats] = useState<SourceStatsResponse | null>(null)
  const [maxLimit, setMaxLimit] = useState(200)
  const [mode, setMode] = useState<CollectionMode>('since_last_sweep')
  const [selected, setSelected] = useState<string[]>([])
  const [startDate, setStartDate] = useState(() => toLocalInput(new Date(Date.now() - 7 * 864e5)))
  const [endDate, setEndDate] = useState(() => toLocalInput(new Date()))
  const [postLimit, setPostLimit] = useState('20')
  const [editing, setEditing] = useState<string | null>(null)

  const [collectionJob, setCollectionJob] = useState<CollectionJob | null>(null)
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null)
  const [history, setHistory] = useState<CollectionJob[]>([])
  const [lastAnalysis, setLastAnalysis] = useState<AnalysisJob | null>(null)
  const [pending, setPending] = useState<number | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [offline, setOffline] = useState(false)
  const [updatedAt, setUpdatedAt] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState<'collect' | 'retry' | 'analyze' | null>(null)

  // Latest job ids without re-creating the refresh callback on every change.
  const shown = useRef<{ collection: number | null; analysis: number | null }>({ collection: null, analysis: null })
  useEffect(() => {
    shown.current = { collection: collectionJob?.id ?? null, analysis: analysisJob?.id ?? null }
  }, [collectionJob?.id, analysisJob?.id])

  /** Everything on the page except the job being polled at POLL_MS. Also
   *  adopts a job started elsewhere (CLI, another browser, a teammate). */
  const refreshAll = useCallback(() => {
    return Promise.all([
      api.getCollectionSources(),
      api.listCollectionJobs(),
      api.listAnalysisJobs(1),
      api.getPendingAnalysis(),
      api.getSourceStats(),
    ])
      .then(([src, jobs, analyses, pend, st]) => {
        setSources(src.sources)
        setMaxLimit(src.max_post_limit)
        setHistory(jobs.results)
        setPending(pend.pending_posts)
        setStats(st)
        const latest = jobs.results[0] ?? null
        if (latest && (isActive(latest.status) || shown.current.collection === null)) setCollectionJob(latest)
        const la = analyses.results[0] ?? null
        setLastAnalysis(la)
        if (la && isActive(la.status) && shown.current.analysis !== la.id) setAnalysisJob(la)
        setOffline(false)
        setUpdatedAt(Date.now())
        return { src, jobs, la }
      })
  }, [])

  // First load: pre-select every available source; show the latest runs.
  useEffect(() => {
    refreshAll()
      .then(({ src, jobs, la }) => {
        setSelected(src.sources.filter((s) => s.available).map((s) => s.key))
        const latest = jobs.results[0] ?? null
        if (la && (isActive(la.status) || (latest && la.collection_job_id === latest.id))) setAnalysisJob(la)
      })
      .catch((e) => setError(`Could not reach the backend: ${e.message ?? e}`))
      .finally(() => setLoaded(true))
  }, [refreshAll])

  const collecting = isActive(collectionJob?.status)
  const analyzing = isActive(analysisJob?.status)

  const pollCollection = useCallback(() => {
    if (!collectionJob) return
    api
      .getCollectionJob(collectionJob.id)
      .then((j) => {
        setCollectionJob(j)
        if (!isActive(j.status)) refreshAll().catch(() => {})
      })
      .catch(() => {}) // transient; next tick retries
  }, [collectionJob, refreshAll])

  const pollAnalysis = useCallback(() => {
    if (!analysisJob) return
    api
      .getAnalysisJob(analysisJob.id)
      .then((j) => {
        setAnalysisJob(j)
        if (!isActive(j.status)) refreshAll().catch(() => {})
      })
      .catch(() => {})
  }, [analysisJob, refreshAll])

  const liveTick = useCallback(() => {
    refreshAll().catch(() => setOffline(true))
  }, [refreshAll])

  usePolling(collecting, POLL_MS, pollCollection)
  usePolling(analyzing, POLL_MS, pollAnalysis)
  usePolling(loaded, LIVE_MS, liveTick)
  const ago = useAgo(updatedAt)

  const availableKeys = sources.filter((s) => s.available).map((s) => s.key)
  const allSelected = availableKeys.length > 0 && availableKeys.every((k) => selected.includes(k))
  const limitNum = Number(postLimit)
  const needsLimit = mode !== 'since_last_sweep'

  let formProblem: string | null = null
  if (selected.length === 0) formProblem = 'Pick at least one source.'
  else if (needsLimit && (!Number.isInteger(limitNum) || limitNum < 1 || limitNum > maxLimit)) {
    formProblem = `Number of posts must be between 1 and ${maxLimit}.`
  } else if (mode === 'custom_range') {
    if (!startDate || !endDate) formProblem = 'Enter both a start and an end date.'
    else if (new Date(startDate) >= new Date(endDate)) formProblem = 'The start must be before the end.'
    else if (new Date(startDate) > new Date()) formProblem = 'The start date is in the future.'
  }
  if (!formProblem && editing) formProblem = 'Save or cancel the source edit first.'

  const busy = collecting || analyzing
  const toggle = (key: string) =>
    setSelected((cur) => (cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key]))

  const startCollection = () => {
    const req: CollectionJobRequest = { mode, sources: selected }
    if (needsLimit) req.post_limit = limitNum
    if (mode === 'custom_range') {
      req.start_date = new Date(startDate).toISOString()
      req.end_date = new Date(endDate).toISOString()
    }
    setSubmitting('collect')
    setError(null)
    setAnalysisJob(null)
    api
      .startCollection(req)
      .then((j) => {
        setCollectionJob(j)
        setHistory((h) => [j, ...h])
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setSubmitting(null))
  }

  const retry = () => {
    if (!collectionJob) return
    setSubmitting('retry')
    setError(null)
    api
      .retryCollection(collectionJob.id)
      .then((j) => {
        setCollectionJob(j)
        setHistory((h) => [j, ...h])
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setSubmitting(null))
  }

  const startAnalysis = () => {
    setSubmitting('analyze')
    setError(null)
    api
      .startAnalysis(collectionJob?.id)
      .then(setAnalysisJob)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setSubmitting(null))
  }

  const onSourceSaved = (updated: CollectionSource) => {
    setSources((cur) => cur.map((s) => (s.key === updated.key ? updated : s)))
    setEditing(null)
  }

  if (!loaded) return <div className="loading">Loading...</div>

  const editingSource = sources.find((s) => s.key === editing) ?? null

  return (
    <div className="data-collection">
      <div className="section-head">
        <div>
          <h2>Data Collection</h2>
          <p className="dc-intro">
            Fetch new posts from the sources, check what came in, then run the SLD analysis to score them for
            the dashboard.
          </p>
        </div>
        <span className={`dc-live ${offline ? 'dc-live-off' : ''}`} role="status">
          <span className="dc-live-dot" aria-hidden="true" />
          {offline ? 'Reconnecting…' : `Live · updated ${ago}`}
        </span>
      </div>

      <CollectionStepper state={stepperState(collectionJob, analysisJob, pending)} />

      {error && <div className="error-banner dc-error">{error}</div>}

      <section className="dc-card">
        <h3>1. What to fetch</h3>
        <div className="dc-modes" role="radiogroup" aria-label="Collection mode">
          {(Object.keys(MODE_LABELS) as CollectionMode[]).map((m) => (
            <label key={m} className={`dc-mode ${mode === m ? 'dc-mode-active' : ''}`}>
              <input
                type="radio"
                name="mode"
                value={m}
                checked={mode === m}
                onChange={() => setMode(m)}
                disabled={busy}
              />
              <span className="dc-mode-title">{MODE_LABELS[m]}</span>
              <span className="dc-mode-help">{MODE_HELP[m]}</span>
            </label>
          ))}
        </div>

        {needsLimit && (
          <div className="dc-params">
            {mode === 'custom_range' && (
              <>
                <label>
                  From
                  <input
                    type="datetime-local"
                    value={startDate}
                    max={endDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    disabled={busy}
                  />
                </label>
                <label>
                  To
                  <input
                    type="datetime-local"
                    value={endDate}
                    min={startDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    disabled={busy}
                  />
                </label>
              </>
            )}
            <label>
              Posts per source (max {maxLimit})
              <input
                type="number"
                min={1}
                max={maxLimit}
                value={postLimit}
                onChange={(e) => setPostLimit(e.target.value)}
                disabled={busy}
              />
            </label>
          </div>
        )}
      </section>

      <section className="dc-card">
        <div className="dc-card-head">
          <h3>2. Sources</h3>
          <label className="dc-all">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={() => setSelected(allSelected ? [] : availableKeys)}
              disabled={busy}
            />
            All sources
          </label>
        </div>
        <div className="dc-source-grid">
          {sources.map((s) => (
            <SourceCard
              key={s.key}
              source={s}
              stat={stats?.sources[s.key]}
              days={stats?.days ?? []}
              selected={selected.includes(s.key)}
              disabled={busy}
              editing={editing === s.key}
              onToggle={() => toggle(s.key)}
              onEdit={() => setEditing(editing === s.key ? null : s.key)}
            />
          ))}
        </div>
      </section>

      {editingSource && (
        <SourceEditor
          key={editingSource.key}
          source={editingSource}
          onSaved={onSourceSaved}
          onClose={() => setEditing(null)}
        />
      )}

      <div className="dc-actions">
        <button
          className="dc-btn dc-btn-primary"
          onClick={startCollection}
          disabled={busy || !!formProblem || submitting !== null}
        >
          {submitting === 'collect' ? 'Starting…' : collecting ? 'Fetching…' : 'Fetch posts'}
        </button>
        <span className="dc-subtle">
          {collecting
            ? 'A collection is running — you can leave this page and come back.'
            : analyzing
              ? 'Wait for the analysis to finish before fetching again.'
              : (formProblem ?? 'Fetching uses the backend’s source credentials; Apify sources cost credits.')}
        </span>
      </div>

      {collectionJob && (
        <CollectionProgress
          job={collectionJob}
          sources={sources}
          onRetry={retry}
          retrying={submitting === 'retry'}
        />
      )}

      <AnalysisPanel
        job={analysisJob}
        pending={pending}
        canStart={!busy && submitting === null}
        starting={submitting === 'analyze'}
        onStart={startAnalysis}
      />

      <CollectionHistory jobs={history} sources={sources} lastAnalysis={lastAnalysis} />
    </div>
  )
}
