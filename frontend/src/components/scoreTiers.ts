import { SCORING_VERSION } from '../api/client'
import type { ScoringVersion } from '../api/types'

/**
 * Dashboard bands for v3 scores.
 *
 * PROVISIONAL: these reuse the old v2 cutoffs (Act >=55, Engage >=30,
 * Watch >=10) until v3 bands are chosen from v3's own score distribution
 * (observed max ~65; not fitted to the gold set). Kept per version so a future
 * scorer can bring its own cutoffs.
 */
const BANDS: Record<ScoringVersion, { high: number; mid: number; watch: number }> = {
  v3: { high: 55, mid: 30, watch: 10 },
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
