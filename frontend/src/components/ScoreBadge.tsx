import { SCORING_VERSION } from '../api/client'
import type { ScoringVersion } from '../api/types'

interface Props {
  score: number | null
}

/**
 * Bands are per scoring version, because the two scales are not comparable.
 *
 * v1 in practice tops out near 40 (its components reach 47 of a nominal 95,
 * then confidence x recency roughly halves that), so its cutoffs sit low.
 * v2 drops both multipliers and uses the full range, with cutoffs taken from
 * the 167-post gold set: Act >=55, Engage >=30, Watch >=10, Discard below.
 * Reusing v1's cutoffs on v2 would mark almost every post "high".
 */
const BANDS: Record<ScoringVersion, { high: number; mid: number; watch: number }> = {
  v1: { high: 20, mid: 10, watch: 4 },
  v2: { high: 55, mid: 30, watch: 10 },
}

function band(score: number): { cls: string; label: string } {
  const b = BANDS[SCORING_VERSION]
  if (score >= b.high) return { cls: 'score-high', label: 'Act — contact or respond' }
  if (score >= b.mid) return { cls: 'score-mid', label: 'Engage — educate or file as intel' }
  if (score >= b.watch) return { cls: 'score-low', label: 'Watch — retain, no action' }
  return { cls: 'score-low', label: 'Discard — no meaningful signal' }
}

export function ScoreBadge({ score }: Props) {
  if (score === null) {
    return (
      <span className="score-badge score-unanalyzed" title="Not analyzed">
        —
      </span>
    )
  }
  const { cls, label } = band(score)
  return (
    <span className={`score-badge ${cls}`} title={`${label} (${SCORING_VERSION})`}>
      {score.toFixed(1)}
    </span>
  )
}
