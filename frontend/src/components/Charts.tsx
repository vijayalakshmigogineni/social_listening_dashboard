import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Bucket } from '../api/types'
import { explorerHref, humanize } from './drill'

/**
 * Single-series count charts for the Overview. One hue (--series-1), so no
 * legend -- the card title names the series. Every mark is a link into All
 * Signals with the exact filter the backend returned for that bucket, and
 * every chart carries a screen-reader table of the same numbers.
 */

/** Axis top rounded up to a clean 1-2-5 step (counts, so steps are whole). */
function niceMax(max: number): number {
  if (max <= 0) return 1
  const raw = max / 4
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const step = Math.max(1, [1, 2, 5, 10].map((s) => s * magnitude).find((s) => s >= raw) ?? raw)
  return Math.ceil(max / step) * step
}

function SrTable({ caption, rows }: { caption: string; rows: [string, number][] }) {
  return (
    <table className="sr-only">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th>Group</th>
          <th>Opportunities</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}>
            <td>{k}</td>
            <td>{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

interface BarListProps {
  title: string
  buckets: Bucket[]
  label?: (key: string) => string
}

/** Horizontal bars, sorted by count (the backend sends them ranked). */
export function BarList({ title, buckets, label = humanize }: BarListProps) {
  const max = Math.max(1, ...buckets.map((b) => b.count))
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      {buckets.length === 0 ? (
        <div className="chart-empty">No opportunities yet</div>
      ) : (
        <div className="bar-list" aria-hidden="true">
          {buckets.map((b) => (
            <Link
              key={b.key}
              to={explorerHref(b.filter)}
              className="bar-row"
              title={`${label(b.key)}: ${b.count} opportunit${b.count === 1 ? 'y' : 'ies'} — view signals`}
            >
              <span className="bar-label">{label(b.key)}</span>
              <span className="bar-track">
                <span className="bar-fill" style={{ width: `${(b.count / max) * 100}%` }} />
                <span className="bar-value">{b.count}</span>
              </span>
            </Link>
          ))}
        </div>
      )}
      <SrTable caption={title} rows={buckets.map((b) => [label(b.key), b.count])} />
    </div>
  )
}

interface ColumnChartProps {
  title: string
  buckets: Bucket[]
  bucket: 'day' | 'week' | 'month'
  note?: string
  onBucketChange: (b: 'day' | 'week' | 'month') => void
}

function periodLabel(key: string, bucket: 'day' | 'week' | 'month', long = false): string {
  const d = new Date(`${key}T00:00:00`)
  if (bucket === 'month') {
    return d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
  }
  const text = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', ...(long ? { year: 'numeric' } : {}) })
  return bucket === 'week' && long ? `Week of ${text}` : text
}

/** Columns over time with a hover tooltip; click drills to that period. */
export function ColumnChart({ title, buckets, bucket, note, onBucketChange }: ColumnChartProps) {
  const [hover, setHover] = useState<number | null>(null)
  const max = niceMax(Math.max(0, ...buckets.map((b) => b.count)))
  const labelEvery = Math.max(1, Math.ceil(buckets.length / 8))

  return (
    <div className="chart-card chart-card-wide">
      <div className="chart-head">
        <h3>{title}</h3>
        <div className="chart-toggle" role="group" aria-label="Bucket size">
          {(['day', 'week', 'month'] as const).map((b) => (
            <button key={b} className={b === bucket ? 'active' : ''} onClick={() => onBucketChange(b)}>
              {humanize(b)}
            </button>
          ))}
        </div>
      </div>
      {buckets.length === 0 ? (
        <div className="chart-empty">No dated opportunities yet</div>
      ) : (
        <div className="column-chart" aria-hidden="true">
          <div className="column-axis">
            <span>{max}</span>
            <span>{max / 2 === Math.round(max / 2) ? max / 2 : ''}</span>
            <span>0</span>
          </div>
          <div className="column-plot" onMouseLeave={() => setHover(null)}>
            <div className="column-grid">
              <span />
              <span />
              <span />
            </div>
            <div className="column-bars">
              {buckets.map((b, i) => (
                <Link
                  key={b.key}
                  to={explorerHref(b.filter)}
                  className={`column-slot${hover === i ? ' is-hover' : ''}`}
                  onMouseEnter={() => setHover(i)}
                  onFocus={() => setHover(i)}
                >
                  <span className="column-fill" style={{ height: `${(b.count / max) * 100}%` }} />
                  {i % labelEvery === 0 && <span className="column-x">{periodLabel(b.key, bucket)}</span>}
                </Link>
              ))}
            </div>
            {hover !== null && buckets[hover] && (
              <div
                className="chart-tooltip"
                style={{ left: `${((hover + 0.5) / buckets.length) * 100}%` }}
              >
                <strong>{buckets[hover].count}</strong> opportunit{buckets[hover].count === 1 ? 'y' : 'ies'}
                <span>{periodLabel(buckets[hover].key, bucket, true)}</span>
              </div>
            )}
          </div>
        </div>
      )}
      {note && <div className="chart-note">{note}</div>}
      <SrTable caption={title} rows={buckets.map((b) => [periodLabel(b.key, bucket, true), b.count])} />
    </div>
  )
}
