import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { PipelineExplanation } from '../api/types'
import { isOpportunityBreakdown } from '../api/types'
import { humanize } from '../components/drill'
import { ScoreContributions } from '../components/ScoreContributions'

function JsonBlock({ data }: { data: unknown }) {
  return <pre className="json-block">{JSON.stringify(data, null, 2)}</pre>
}

function Raw({ label, data }: { label: string; data: unknown }) {
  if (data === undefined) return null
  return (
    <details className="pipeline-raw">
      <summary>{label}</summary>
      <JsonBlock data={data} />
    </details>
  )
}

const conf = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v.toFixed(2))

/**
 * How one record was scored, in pipeline order:
 * input -> Step 1 RCM -> Step 3 taxonomy -> LLM assessment -> normalized
 * components x weights -> final. Stored row by default (exactly what the
 * dashboard shows, no LLM call); "Re-run live" re-runs every stage.
 */
export function PipelineDebug() {
  const { source, sourceItemId } = useParams<{ source: string; sourceItemId: string }>()
  const [live, setLive] = useState(false)
  // Each result is tagged with the request it answers, so switching record or
  // mode shows "loading" instead of the previous record's breakdown.
  const requestKey = `${source}/${sourceItemId}/${live}`
  const [result, setResult] = useState<{ key: string; data: PipelineExplanation } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const explanation = result?.key === requestKey ? result.data : null

  useEffect(() => {
    if (!source || !sourceItemId) return
    const key = `${source}/${sourceItemId}/${live}`
    api
      .explainPipeline(source, sourceItemId, live)
      .then((data) => {
        setResult({ key, data })
        setError(null)
      })
      .catch((e) => setError(String(e)))
  }, [source, sourceItemId, live])

  if (error) return <div className="error-banner">{error}</div>
  if (!explanation) return <div className="loading">{live ? 'Re-running every stage (LLM)...' : 'Loading...'}</div>

  const bd = isOpportunityBreakdown(explanation.score_breakdown) ? explanation.score_breakdown : null
  const a = bd?.llm_assessment ?? null
  const step1 = explanation.step1_rcm_relevance as
    | { rcm_relevant: boolean; rcm_relevance_confidence: number; relevance_method?: string }
    | undefined

  return (
    <div className="pipeline-debug">
      <div className="section-head">
        <h2>
          Pipeline breakdown — {source}:{sourceItemId}
        </h2>
        <button className="dc-btn dc-btn-secondary" onClick={() => setLive(!live)}>
          {live ? 'Show stored result' : 'Re-run live (calls LLM)'}
        </button>
      </div>
      <p className="pipeline-versions">
        {explanation.mode === 'stored' ? 'Stored result' : 'Live re-run (not saved)'} ·
        analysis_version={explanation.analysis_version} · scoring_version={explanation.scoring_version ?? '—'}
        {' · '}
        <Link to={`/posts/${source}/${sourceItemId}`}>signal detail</Link>
      </p>

      <div className="pipeline-stage">
        <h3>Input</h3>
        <div className="post-detail-text">{explanation.input_text}</div>
        <Raw label="Raw record" data={explanation.raw_record} />
        <Raw label="Normalized record" data={explanation.normalized_record} />
      </div>

      {!explanation.analyzed ? (
        <div className="pipeline-stage">
          <p>
            Not analyzed under the current version yet. Run <code>python scripts/run_pipeline.py</code> or
            re-run live above.
          </p>
        </div>
      ) : (
        <>
          <div className="pipeline-stage">
            <h3>Step 1 — RCM relevance</h3>
            {step1 && (
              <p>
                {step1.rcm_relevant ? 'RCM relevant' : 'Not RCM relevant (pipeline stops; score 0)'} · confidence{' '}
                {conf(step1.rcm_relevance_confidence)}
                {step1.relevance_method && ` · decided by ${step1.relevance_method}`}
              </p>
            )}
            <Raw label="Step 1 output" data={explanation.step1_rcm_relevance} />
          </div>

          <div className="pipeline-stage">
            <h3>Step 3 — Payer / procedure / taxonomy</h3>
            <Raw label="Step 3 output" data={explanation.step3_taxonomy} />
            {!explanation.step3_taxonomy && <p className="dc-subtle">—</p>}
          </div>

          <div className="pipeline-stage">
            <h3>LLM human-like opportunity assessment</h3>
            {a ? (
              <>
                <table className="dc-table">
                  <tbody>
                    <tr><td>Problem evidence</td><td>{a.problem_evidence ? 'yes' : 'no'}</td><td className="num">conf {conf(a.problem_confidence)}</td></tr>
                    <tr><td>First person</td><td>{a.first_person ? 'yes' : 'no'}</td><td className="num">conf {conf(a.first_person_confidence)}</td></tr>
                    <tr><td>Recurring</td><td>{a.problem_recurring ? 'yes' : 'no'}</td><td className="num" /></tr>
                    <tr><td>Seeking level</td><td>{a.seeking_level ?? 'none'}</td><td className="num">conf {conf(a.seeking_confidence)}</td></tr>
                    <tr><td>Business impact</td><td>{a.business_impact ?? '—'}</td><td className="num">conf {conf(a.impact_confidence)}</td></tr>
                    <tr><td>Pain severity</td><td>{a.pain_severity ?? '—'}</td><td className="num">conf {conf(a.pain_confidence)}</td></tr>
                    <tr><td>ProbePS fit</td><td>{a.probeps_fit ?? '—'}</td><td className="num">conf {conf(a.fit_confidence)}</td></tr>
                    <tr><td>Opportunity type</td><td>{a.opportunity_type ? humanize(a.opportunity_type) : '—'}</td><td className="num" /></tr>
                    <tr><td>Speaker / stance</td><td>{a.speaker_type} / {a.content_stance}</td><td className="num" /></tr>
                  </tbody>
                </table>
                {a.opportunity_reasoning && <p className="assessment-reason">{a.opportunity_reasoning}</p>}
                {a.semantic_source === 'fallback' && (
                  <p className="dc-bad">LLM unavailable: rule fallback produced these fields; opportunity fields score 0.</p>
                )}
              </>
            ) : (
              <p className="dc-subtle">No LLM assessment (not RCM relevant, or stored by an older analysis version).</p>
            )}
            <Raw label="Full semantic output" data={explanation.step2_semantic ?? a ?? undefined} />
          </div>

          <div className="pipeline-stage">
            <h3>Normalized scores → 65 / 20 / 15 contributions → final opportunity score</h3>
            {bd ? (
              <ScoreContributions breakdown={bd} detailed />
            ) : (
              <p className="dc-subtle">This row was scored by an older scorer; re-analyze it to see the breakdown.</p>
            )}
            <Raw label="Stored score_breakdown" data={explanation.score_breakdown} />
          </div>
        </>
      )}
    </div>
  )
}
