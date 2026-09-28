/**
 * Dashboard bands for the ProbePS opportunity score (0-100).
 *
 * Engage starts at the backend's OPPORTUNITY_THRESHOLD (40,
 * app/analysis/scoring_opportunity.py), so every Engage/Act post is counted
 * as an opportunity when it has problem evidence. PROVISIONAL: set all three
 * cutoffs from the real score distribution and the gold set
 * (scripts/rescore.py --dry-run) before relying on them.
 */
const BANDS = { high: 60, mid: 40, watch: 20 }

export type ScoreTier = 'Act' | 'Engage' | 'Watch' | 'Discard'

export const SCORE_TIERS: ScoreTier[] = ['Act', 'Engage', 'Watch', 'Discard']

export function scoreTier(score: number): ScoreTier {
  if (score >= BANDS.high) return 'Act'
  if (score >= BANDS.mid) return 'Engage'
  if (score >= BANDS.watch) return 'Watch'
  return 'Discard'
}