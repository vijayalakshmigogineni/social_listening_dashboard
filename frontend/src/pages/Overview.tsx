import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Post, Summary } from '../api/types'
import { PostCard } from '../components/PostCard'

export function Overview() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [recent, setRecent] = useState<Post[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getSummary().then(setSummary).catch((e) => setError(String(e)))
    api
      .listPosts({ sort: 'score_desc', page_size: 12 })
      .then((r) => setRecent(r.results))
      .catch((e) => setError(String(e)))
  }, [])

  if (error) return <div className="error-banner">{error}</div>
  if (!summary) return <div className="loading">Loading...</div>

  return (
    <div className="overview">
      <section className="stat-row">
        <div className="stat-tile">
          <div className="stat-value">{summary.total_posts}</div>
          <div className="stat-label">Total posts collected</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{summary.total_rcm_relevant}</div>
          <div className="stat-label">RCM-relevant</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{summary.total_problem_evidence}</div>
          <div className="stat-label">Problem evidence found</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{summary.avg_score ?? '—'}</div>
          <div className="stat-label">Average signal score</div>
        </div>
      </section>

      <section className="breakdown-row">
        <div className="breakdown-card">
          <h3>By source</h3>
          {Object.entries(summary.by_source).map(([k, v]) => (
            <div key={k} className="breakdown-line">
              <span>{k}</span>
              <span>{v}</span>
            </div>
          ))}
        </div>
        <div className="breakdown-card">
          <h3>By problem category</h3>
          {Object.entries(summary.by_problem_category).map(([k, v]) => (
            <div key={k} className="breakdown-line">
              <span>{k.replaceAll('_', ' ')}</span>
              <span>{v}</span>
            </div>
          ))}
        </div>
        <div className="breakdown-card">
          <h3>By seeking level</h3>
          {Object.entries(summary.by_seeking_level).map(([k, v]) => (
            <div key={k} className="breakdown-line">
              <span>{k === 'null' ? 'not applicable' : k}</span>
              <span>{v}</span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>Recent high-priority signals</h2>
        <div className="post-grid">
          {recent.map((p) => (
            <PostCard key={`${p.source}:${p.source_item_id}`} post={p} />
          ))}
        </div>
      </section>
    </div>
  )
}
