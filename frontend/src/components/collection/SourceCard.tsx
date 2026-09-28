import { Link } from 'react-router-dom'
import type { CollectionSource, SourceStat } from '../../api/types'
import { explorerHref } from '../drill'
import { fmtDateTime, plural } from './format'

interface Props {
  source: CollectionSource
  stat: SourceStat | undefined
  days: string[]
  selected: boolean
  disabled: boolean
  editing: boolean
  onToggle: () => void
  onEdit: () => void
}

function checkpointText(s: CollectionSource): string {
  const cp = s.checkpoint
  if (cp.last_successful_fetch) return `Last sweep ${fmtDateTime(cp.last_successful_fetch)}`
  if (cp.next_sweep_from_origin === 'newest_stored_post') {
    return `Not swept yet — starts from newest stored post (${fmtDateTime(cp.next_sweep_from)})`
  }
  return 'Not swept yet — would fetch the last 7 days'
}

/** Posts collected per day, last N days: one hue, hover shows the count. */
function Sparkline({ values, days }: { values: number[]; days: string[] }) {
  const max = Math.max(1, ...values)
  const w = 6
  const gap = 2
  const h = 28
  return (
    <svg
      className="dc-spark"
      viewBox={`0 0 ${values.length * (w + gap) - gap} ${h}`}
      width={values.length * (w + gap) - gap}
      height={h}
      role="img"
      aria-label={`Posts collected per day, last ${values.length} days: ${values.join(', ')}`}
    >
      {values.map((v, i) => {
        const bh = v === 0 ? 2 : Math.max(3, (v / max) * h)
        return (
          <rect
            key={days[i] ?? i}
            x={i * (w + gap)}
            y={h - bh}
            width={w}
            height={bh}
            rx={1.5}
            className={v === 0 ? 'dc-spark-empty' : 'dc-spark-bar'}
          >
            <title>{`${days[i] ?? ''}: ${v} post${v === 1 ? '' : 's'} collected`}</title>
          </rect>
        )
      })}
    </svg>
  )
}

export function SourceCard({ source, stat, days, selected, disabled, editing, onToggle, onEdit }: Props) {
  const collected14 = stat ? stat.collected_per_day.reduce((a, b) => a + b, 0) : 0
  return (
    <div
      className={`dc-source-card ${selected ? 'dc-source-on' : ''} ${source.available ? '' : 'dc-source-off'} ${editing ? 'dc-source-editing' : ''}`}
    >
      <div className="dc-source-top">
        <label className="dc-source-pick">
          <input type="checkbox" checked={selected} onChange={onToggle} disabled={disabled || !source.available} />
          <span className={`source-tag source-${source.key}`}>{source.label}</span>
          {source.customized && <span className="dc-badge">Edited</span>}
        </label>
        <button className="dc-link-btn" onClick={onEdit} disabled={disabled}>
          {editing ? 'Editing…' : `Edit ${plural(source.unit_label)}`}
        </button>
      </div>

      {stat && (
        <div className="dc-source-stats">
          <Link to={explorerHref({ source: source.key })} className="dc-stat" title="All posts from this source">
            <span className="dc-stat-value">{stat.posts}</span>
            <span className="dc-stat-label">Posts</span>
          </Link>
          <div className="dc-stat" title="Scored by the current analysis version">
            <span className="dc-stat-value">{stat.analyzed}</span>
            <span className="dc-stat-label">Analyzed</span>
          </div>
          <Link
            to={explorerHref({ source: source.key, opportunity: true })}
            className="dc-stat dc-stat-accent"
            title="Opportunities from this source"
          >
            <span className="dc-stat-value">{stat.opportunities}</span>
            <span className="dc-stat-label">Opportunities</span>
          </Link>
          <div className={`dc-stat ${stat.pending > 0 ? 'dc-stat-warn' : ''}`} title="Collected but not analyzed yet">
            <span className="dc-stat-value">{stat.pending}</span>
            <span className="dc-stat-label">Pending</span>
          </div>
        </div>
      )}

      {stat && (
        <div className="dc-source-trend">
          <Sparkline values={stat.collected_per_day} days={days} />
          <span className="dc-subtle">
            {collected14} collected in {days.length} days
            {stat.last_collected_at && <> · last {fmtDateTime(stat.last_collected_at)}</>}
          </span>
        </div>
      )}

      <div className="dc-source-foot">
        <span className="dc-subtle">
          {source.available ? checkpointText(source) : `Unavailable: ${source.unavailable_reason}`}
        </span>
        <span className="dc-subtle" title={source.units.join(', ')}>
          {source.units.length} {plural(source.unit_label, source.units.length)} · {source.cost_note}
        </span>
      </div>
    </div>
  )
}
