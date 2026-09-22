import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Post } from '../api/types'
import { ScoreBadge } from '../components/ScoreBadge'

export function PostDetail() {
  const { source, sourceItemId } = useParams<{ source: string; sourceItemId: string }>()
  const [post, setPost] = useState<Post | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!source || !sourceItemId) return
    api.getPost(source, sourceItemId).then(setPost).catch((e) => setError(String(e)))
  }, [source, sourceItemId])

  if (error) return <div className="error-banner">{error}</div>
  if (!post) return <div className="loading">Loading...</div>

  const breakdown = post.score_breakdown

  return (
    <div className="post-detail">
      <div className="post-detail-header">
        <span className={`source-tag source-${post.source}`}>{post.source}</span>
        <ScoreBadge score={post.final_score} />
        <Link to={`/pipeline/${post.source}/${post.source_item_id}`} className="debug-link">
          View pipeline breakdown →
        </Link>
      </div>

      {post.title && <h1>{post.title}</h1>}

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

        {breakdown && (
          <div className="detail-section">
            <h3>Score breakdown</h3>
            <dl>
              <dt>Problem strength</dt>
              <dd>{breakdown.problem_strength} / 20</dd>
              <dt>Market relevance</dt>
              <dd>{breakdown.market_relevance} / 20</dd>
              <dt>Intent strength</dt>
              <dd>{breakdown.intent_strength} / 30</dd>
              <dt>Specificity</dt>
              <dd>{breakdown.specificity} / 15</dd>
              <dt>Severity</dt>
              <dd>{breakdown.severity} / 10</dd>
              <dt>Base score</dt>
              <dd>{breakdown.base_score}</dd>
              <dt>Confidence adjustment</dt>
              <dd>× {breakdown.confidence}</dd>
              <dt>Recency adjustment</dt>
              <dd>× {breakdown.recency_factor}</dd>
              <dt>
                <strong>Final score</strong>
              </dt>
              <dd>
                <strong>{breakdown.final_score}</strong>
              </dd>
            </dl>
          </div>
        )}
      </div>

      {post.evidence_quote && (
        <div className="evidence-block">
          <h3>Evidence quote</h3>
          <blockquote>"{post.evidence_quote}"</blockquote>
        </div>
      )}
    </div>
  )
}
