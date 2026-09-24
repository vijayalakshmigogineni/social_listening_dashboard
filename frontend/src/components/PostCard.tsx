import { Link } from 'react-router-dom'
import type { Post } from '../api/types'
import { ScoreBadge } from './ScoreBadge'

interface Props {
  post: Post
}

function formatDate(iso: string | null): string {
  if (!iso) return 'unknown date'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatCategory(cat: string): string {
  return cat
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ')
}

/** Where a comment-style record came from, e.g. the YouTube video and channel
 * it was posted under. Null for sources whose records stand on their own. */
export function sourceContext(post: Post): string | null {
  if (post.source !== 'youtube') return null
  const m = post.source_metadata ?? {}
  const parts = [m.channel_name, m.video_published_at && `video ${formatDate(String(m.video_published_at))}`]
  if (m.published_time_text) parts.push(`${m.is_reply ? 'reply' : 'comment'} ${m.published_time_text}`)
  return parts.filter(Boolean).join(' · ') || null
}

export function PostCard({ post }: Props) {
  const snippet = post.evidence_quote || post.text?.slice(0, 220) || post.title || ''
  const context = sourceContext(post)

  return (
    <Link
      to={`/posts/${encodeURIComponent(post.source)}/${encodeURIComponent(post.source_item_id)}`}
      className="post-card"
    >
      <div className="post-card-header">
        <span className={`source-tag source-${post.source}`}>{post.source}</span>
        <span className="post-date">{formatDate(post.created_at)}</span>
        <ScoreBadge score={post.final_score} />
      </div>

      {post.title && <div className="post-title">{post.title}</div>}
      {context && <div className="post-context">{context}</div>}
      <div className="post-snippet">{snippet}</div>

      <div className="post-tags">
        {post.problem_category.map((c) => (
          <span key={c} className="tag tag-category">
            {formatCategory(c)}
          </span>
        ))}
        {post.payer_tags.map((p) => (
          <span key={p} className="tag tag-payer">
            {p}
          </span>
        ))}
        {post.seeking_level && <span className="tag tag-seeking">{post.seeking_level}</span>}
        {post.content_stance && <span className="tag tag-stance">{post.content_stance}</span>}
      </div>
    </Link>
  )
}
