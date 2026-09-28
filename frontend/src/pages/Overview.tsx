import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Kpi, OverviewResponse } from '../api/types'
import { BarList, ColumnChart } from '../components/Charts'
import { explorerHref } from '../components/drill'
import { PostCard } from '../components/PostCard'

/**
 * ProbePS opportunity Overview. Every number comes from /api/stats/overview;
 * each card, bar and column links to All Signals with the backend-supplied
 * filter that reproduces its count.
 */
export function Overview() {
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [bucket, setBucket] = useState<'day' | 'week' | 'month'>('month')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getOverview(bucket)
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e) => setError(String(e)))
  }, [bucket])

  if (error) return <div className="error-banner">{error}</div>
  if (!data) return <div className="loading">Loading...</div>

  const { kpis, series, top, definitions } = data
  const overTime = series.opportunities_over_time

  return (
    <div className="overview">
      <section className="stat-row stat-row-3">
        <KpiCard primary kpi={kpis.total_opportunities} label="Total Opportunities"
          hint={`Problem evidence and score ≥ ${definitions.opportunity_threshold}`} />
        <KpiCard kpi={kpis.new_today} label="New Today"
          hint={`Opportunities collected since 00:00 ${definitions.report_tz}`} />
        <KpiCard kpi={kpis.rcm_relevant} label="RCM Relevant" hint="Posts about revenue cycle management" />
      </section>

      <section className="chart-grid">
        <ColumnChart
          title="Opportunities Over Time"
          buckets={overTime.points}
          bucket={overTime.bucket}
          onBucketChange={setBucket}
          note={overTimeNote(overTime.earlier, overTime.undated)}
        />
        <BarList title="Problem Category Distribution" buckets={series.problem_category} />
        <BarList title="Source Contribution" buckets={series.source_contribution} label={(k) => k} />
        <BarList title="Seeking Level Distribution" buckets={series.seeking_level} label={seekingLabel} />
      </section>

      <section>
        <div className="section-head">
          <h2>Top 3 Opportunity Signals</h2>
          <Link to={explorerHref({ opportunity: true, sort: 'score_desc' })} className="view-all">
            View All Signals →
          </Link>
        </div>
        {top.length === 0 ? (
          <div className="chart-empty">No opportunities scored yet.</div>
        ) : (
          <div className="post-grid">
            {top.map((p) => (
              <PostCard key={`${p.source}:${p.source_item_id}`} post={p} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function KpiCard({ kpi, label, hint, primary = false }: { kpi: Kpi; label: string; hint: string; primary?: boolean }) {
  return (
    <Link to={explorerHref(kpi.filter)} className={`stat-tile stat-tile-link${primary ? ' stat-tile-primary' : ''}`} title={`${hint} — view signals`}>
      <div className="stat-value">{kpi.value.toLocaleString()}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-hint">{hint}</div>
    </Link>
  )
}

function overTimeNote(earlier: number, undated: number): string | undefined {
  const parts = []
  if (earlier > 0) parts.push(`${earlier} older opportunit${earlier === 1 ? 'y is' : 'ies are'} before this window`)
  if (undated > 0) parts.push(`${undated} ha${undated === 1 ? 's' : 've'} no post date`)
  return parts.length ? `Not shown: ${parts.join('; ')}.` : undefined
}

const SEEKING_LABELS: Record<string, string> = {
  L0: 'L0 · describes problem',
  L1: 'L1 · asks for help',
  L2: 'L2 · wants a solution',
  L3: 'L3 · wants a vendor',
  none: 'Not seeking',
}

function seekingLabel(key: string): string {
  return SEEKING_LABELS[key] ?? key
}
