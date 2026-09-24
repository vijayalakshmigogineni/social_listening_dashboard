import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type {
  AnalysisJob,
  CollectionJob,
  CollectionJobRequest,
  CollectionMode,
  CollectionSource,
} from '../api/types'
import { AnalysisPanel } from '../components/collection/AnalysisPanel'
import { CollectionHistory } from '../components/collection/CollectionHistory'
import { CollectionProgress } from '../components/collection/CollectionProgress'
import { MODE_LABELS, fmtDateTime, isActive, plural, toLocalInput } from '../components/collection/format'

const POLL_MS = 1500

const MODE_HELP: Record<CollectionMode, string> = {
  since_last_sweep:
    'Everything posted since each source was last swept, up to now. The time range is worked out for you.',
  custom_range: 'Posts made between two dates, up to a number of posts per source.',
  latest_n: 'The newest posts from each source, whenever they were made.',
}

/** Re-run `tick` every POLL_MS while `active`. */
function usePolling(active: boolean, tick: () => void) {
  useEffect(() => {
    if (!active) return
    const id = setInterval(tick, POLL_MS)
    return () => clearInterval(id)
  }, [active, tick])
}

function checkpointText(s: CollectionSource): string {
  const cp = s.checkpoint
  if (cp.last_successful_fetch) return `Last sweep ${fmtDateTime(cp.last_successful_fetch)}`
  if (cp.next_sweep_from_origin === 'newest_stored_post') {
    return `Not swept yet — would start from newest stored post (${fmtDateTime(cp.next_sweep_from)})`
  }
  return 'Not swept yet — would fetch the last 7 days'
}

export function DataCollection() {
  const [sources, setSources] = useState<CollectionSource[]>([])
  const [maxLimit, setMaxLimit] = useState(200)
  const [mode, setMode] = useState<CollectionMode>('since_last_sweep')
  const [selected, setSelected] = useState<string[]>([])
  const [startDate, setStartDate] = useState(() => toLocalInput(new Date(Date.now() - 7 * 864e5)))
  const [endDate, setEndDate] = useState(() => toLocalInput(new Date()))
  const [postLimit, setPostLimit] = useState('20')

  const [collectionJob, setCollectionJob] = useState<CollectionJob | null>(null)
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null)
  const [history, setHistory] = useState<CollectionJob[]>([])
  const [lastAnalysis, setLastAnalysis] = useState<AnalysisJob | null>(null)
  const [pending, setPending] = useState<number | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<'collect' | 'retry' | 'analyze' | null>(null)

  const refreshSideData = useCallback(() => {
    api
      .getCollectionSources()
      .then((r) => {
        setSources(r.sources)
        setMaxLimit(r.max_post_limit)
      })
      .catch((e) => setError(String(e.message ?? e)))
    api.listCollectionJobs().then((r) => setHistory(r.results)).catch(() => {})
    api.getPendingAnalysis().then((r) => setPending(r.pending_posts)).catch(() => {})
    api
      .listAnalysisJobs(1)
      .then((r) => setLastAnalysis(r.results[0] ?? null))
      .catch(() => {})
  }, [])

  // First load: sources, history, and whatever job is still running (or ran last).
  useEffect(() => {
    Promise.all([api.getCollectionSources(), api.listCollectionJobs(), api.listAnalysisJobs(1), api.getPendingAnalysis()])
      .then(([src, jobs, analyses, pend]) => {
        setSources(src.sources)
        setMaxLimit(src.max_post_limit)
        setSelected(src.sources.filter((s) => s.available).map((s) => s.key))
        setHistory(jobs.results)
        setPending(pend.pending_posts)
        const latest = jobs.results[0] ?? null
        setCollectionJob(latest)
        const la = analyses.results[0] ?? null
        setLastAnalysis(la)
        if (la && (isActive(la.status) || (latest && la.collection_job_id === latest.id))) {
          setAnalysisJob(la)
        }
      })
      .catch((e) => setError(`Could not reach the backend: ${e.message ?? e}`))
      .finally(() => setLoaded(true))
  }, [])

  const collecting = isActive(collectionJob?.status)
  const analyzing = isActive(analysisJob?.status)

  const pollCollection = useCallback(() => {
    if (!collectionJob) return
    api
      .getCollectionJob(collectionJob.id)
      .then((j) => {
        setCollectionJob(j)
        if (!isActive(j.status)) refreshSideData()
      })
      .catch(() => {}) // transient; next tick retries
  }, [collectionJob, refreshSideData])

  const pollAnalysis = useCallback(() => {
    if (!analysisJob) return
    api
      .getAnalysisJob(analysisJob.id)
      .then((j) => {
        setAnalysisJob(j)
        if (!isActive(j.status)) refreshSideData()
      })
      .catch(() => {})
  }, [analysisJob, refreshSideData])

  usePolling(collecting, pollCollection)
  usePolling(analyzing, pollAnalysis)

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

  if (!loaded) return <div className="loading">Loading...</div>

  return (
    <div className="data-collection">
      <h2>Data Collection</h2>
      <p className="dc-intro">
        Fetch new posts from the sources, check what came in, then run the SLD analysis to score them
        for the dashboard.
      </p>

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
        <div className="dc-sources">
          {sources.map((s) => (
            <label
              key={s.key}
              className={`dc-source ${selected.includes(s.key) ? 'dc-source-on' : ''} ${s.available ? '' : 'dc-source-off'}`}
            >
              <input
                type="checkbox"
                checked={selected.includes(s.key)}
                onChange={() => toggle(s.key)}
                disabled={busy || !s.available}
              />
              <span className="dc-source-body">
                <span className={`source-tag source-${s.key}`}>{s.label}</span>
                <span className="dc-subtle">
                  {s.available ? checkpointText(s) : `Unavailable: ${s.unavailable_reason}`}
                </span>
                <span className="dc-subtle">
                  {s.units.length} {plural(s.unit_label, s.units.length)} · {s.cost_note}
                </span>
              </span>
            </label>
          ))}
        </div>
      </section>

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
