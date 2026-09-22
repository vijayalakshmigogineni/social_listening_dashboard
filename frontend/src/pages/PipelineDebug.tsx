import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { PipelineExplanation } from '../api/types'

function JsonBlock({ data }: { data: unknown }) {
  return <pre className="json-block">{JSON.stringify(data, null, 2)}</pre>
}

export function PipelineDebug() {
  const { source, sourceItemId } = useParams<{ source: string; sourceItemId: string }>()
  const [explanation, setExplanation] = useState<PipelineExplanation | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!source || !sourceItemId) return
    api.explainPipeline(source, sourceItemId).then(setExplanation).catch((e) => setError(String(e)))
  }, [source, sourceItemId])

  if (error) return <div className="error-banner">{error}</div>
  if (!explanation) return <div className="loading">Loading...</div>

  return (
    <div className="pipeline-debug">
      <h2>
        Pipeline breakdown — {source}:{sourceItemId}
      </h2>
      <p className="pipeline-versions">
        analysis_version={explanation.analysis_version} · scoring_version={explanation.scoring_version}
      </p>

      <div className="pipeline-stage">
        <h3>Raw record</h3>
        <JsonBlock data={explanation.raw_record} />
      </div>

      <div className="pipeline-stage">
        <h3>Normalized record</h3>
        <JsonBlock data={explanation.normalized_record} />
      </div>

      <div className="pipeline-stage">
        <h3>Step 1 — RCM relevance</h3>
        <JsonBlock data={explanation.step1_rcm_relevance} />
      </div>

      <div className="pipeline-stage">
        <h3>Step 2 — Problem evidence</h3>
        <JsonBlock data={explanation.step2_problem_evidence} />
      </div>

      <div className="pipeline-stage">
        <h3>Step 3 — Taxonomy / entity extraction</h3>
        <JsonBlock data={explanation.step3_taxonomy} />
      </div>

      <div className="pipeline-stage">
        <h3>Step 4 — Speaker / stance / seeking</h3>
        <JsonBlock data={explanation.step4_context} />
      </div>

      <div className="pipeline-stage">
        <h3>Step 5 — Evidence + confidence</h3>
        <JsonBlock data={explanation.step5_evidence_confidence} />
      </div>

      <div className="pipeline-stage">
        <h3>Step 6/7 — Scoring</h3>
        <JsonBlock data={explanation.step6_7_scoring} />
      </div>
    </div>
  )
}
