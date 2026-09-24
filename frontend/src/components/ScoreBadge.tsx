import { SCORING_VERSION } from '../api/client'
import { type ScoreTier, scoreTier } from './scoreTiers'

interface Props {
  score: number | null
}

const TIER_DISPLAY: Record<ScoreTier, { cls: string; label: string }> = {
  Act: { cls: 'score-high', label: 'Act — contact or respond' },
  Engage: { cls: 'score-mid', label: 'Engage — educate or file as intel' },
  Watch: { cls: 'score-low', label: 'Watch — retain, no action' },
  Discard: { cls: 'score-low', label: 'Discard — no meaningful signal' },
}

function band(score: number): { cls: string; label: string } {
  return TIER_DISPLAY[scoreTier(score)]
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
