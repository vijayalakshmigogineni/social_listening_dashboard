import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { isOpportunityBreakdown } from '../api/types'
import type { Post } from '../api/types'
import { humanize } from '../components/drill'
import { ScoreBadge } from '../components/ScoreBadge'
import { ScoreContributions } from '../components/ScoreContributions'
import { sourceContext } from '../components/PostCard'

export function PostDetail() {
  const { source, sourceItemId } = useParams<{ source: string; sourceItemId: string }>()
  const [post, setPost] = useState<Post | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  // Go back in history when we arrived from within the app; otherwise
  // (direct link / new tab) fall back to the signals list.
  const goBack = () => {
    if (window.history.state?.idx > 0) navigate(-1)
    else navigate('/explorer')
  }

  useEffect(() => {
    if (!source || !sourceItemId) return
    api.getPost(source, sourceItemId).then(setPost).catch((e) => setError(String(e)))
  }, [source, sourceItemId])

  if (error) return <div className="error-banner">{error}</div>
  if (!post) return <div className="loading">Loading...</div>

  const breakdown = isOpportunityBreakdown(post.score_breakdown) ? post.score_breakdown : null
  const assessment = breakdown?.llm_assessment ?? null

  return (
    <div className="post-detail">
      <button type="button" className="back-link" onClick={goBack}>
        ← Back
      </button>
      <div className="post-detail-header">
        <span className={`source-tag source-${post.source}`}>{post.source}</span>
        <ScoreBadge score={post.final_score} />
        {post.is_opportunity && <span className="tag tag-opportunity">Opportunity</span>}
        <Link to={`/pipeline/${post.source}/${post.source_item_id}`} className="debug-link">
          View pipeline breakdown →
        </Link>
      </div>

      {post.title && <h1>{post.title}</h1>}
      {sourceContext(post) && <div className="post-context">{sourceContext(post)}</div>}

      <div className="post-detail-meta">
        <span>{post.author_name ?? 'Unknown author'}</span>
        {post.author_role && <span>· {post.author_role}</span>}
        {post.created_at && <span>· {new Date(post.created_at).toLocaleString()}</span>}
        {post.url && (
          <a href={post.url} target="_blank" rel="noreferrer" className="original-link">
            Open original source →
          </a>
        )}
      </div>

      <div className="post-detail-text">{post.text}</div>

      <div className="detail-grid">
        <div className="detail-section">
          <h3>Classification</h3>
          <dl>
            <dt>RCM relevant</dt>
            <dd>{post.rcm_relevant === null ? 'not analyzed' : post.rcm_relevant ? 'Yes' : 'No'}</dd>
            <dt>Problem evidence</dt>
            <dd>{post.problem_evidence === null ? 'not analyzed' : post.problem_evidence ? 'Yes' : 'No'}</dd>
            <dt>Problem category</dt>
            <dd>{post.problem_category.join(', ') || '—'}</dd>
            <dt>Payer</dt>
            <dd>{post.payer_tags.join(', ') || '—'}</dd>
            <dt>Procedure</dt>
            <dd>{post.procedure_tags.join(', ') || '—'}</dd>
            <dt>Denial reason</dt>
            <dd>{post.denial_reason_tags.join(', ') || '—'}</dd>
            <dt>Specialty</dt>
            <dd>{post.specialty ?? '—'}</dd>
          </dl>
        </div>

        <div className="detail-section">
          <h3>Speaker &amp; intent</h3>
          <dl>
            <dt>Speaker type</dt>
            <dd>{post.speaker_type ?? '—'}</dd>
            <dt>Stance</dt>
            <dd>{post.content_stance ?? '—'}</dd>
            <dt>Seeking level</dt>
            <dd>{post.seeking_level ?? 'not applicable'}</dd>
            <dt>Confidence</dt>
            <dd>{post.confidence !== null ? post.confidence.toFixed(2) : '—'}</dd>
          </dl>
        </div>

        <div className="detail-section">
          <h3>ProbePS opportunity</h3>
          {assessment ? (
            <dl>
              <dt>Opportunity type</dt>
              <dd>{assessment.opportunity_type ? humanize(assessment.opportunity_type) : '—'}</dd>
              <dt>ProbePS fit</dt>
              <dd>{assessment.probeps_fit ?? '—'}</dd>
              <dt>Business impact</dt>
              <dd>{assessment.business_impact ?? '—'}</dd>
              <dt>Pain severity</dt>
              <dd>{assessment.pain_severity ?? '—'}</dd>
              <dt>Recurring</dt>
              <dd>{assessment.problem_recurring ? 'Yes' : 'No'}</dd>
              <dt>Assessed by</dt>
              <dd>{assessment.semantic_source === 'llm' ? 'LLM' : 'rule fallback (LLM unavailable)'}</dd>
            </dl>
          ) : (
            <p className="dc-subtle">No LLM assessment stored for this post.</p>
          )}
          {assessment?.opportunity_reasoning && <p className="assessment-reason">{assessment.opportunity_reasoning}</p>}
        </div>      </div>

      {breakdown && (
        <div className="detail-section score-section">
          <h3>Score breakdown</h3>
          <ScoreContributions breakdown={breakdown} />
        </div>
      )}

      {post.evidence_quote && (
        <div className="evidence-block">
          <h3>Evidence quote</h3>
          <blockquote>"{post.evidence_quote}"</blockquote>
        </div>
      )}
    </div>
  )
}
