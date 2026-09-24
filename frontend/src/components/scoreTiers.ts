import { SCORING_VERSION } from '../api/client'
import type { ScoringVersion } from '../api/types'

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

export type ScoreTier = 'Act' | 'Engage' | 'Watch' | 'Discard'

export const SCORE_TIERS: ScoreTier[] = ['Act', 'Engage', 'Watch', 'Discard']

export function scoreTier(score: number, version: ScoringVersion = SCORING_VERSION): ScoreTier {
  const b = BANDS[version]
  if (score >= b.high) return 'Act'
  if (score >= b.mid) return 'Engage'
  if (score >= b.watch) return 'Watch'
  return 'Discard'
}
