import type { DrillFilter, PostFilters } from '../api/types'

/** Filters the Explorer URL can carry, and how to parse each back. */
const BOOLEAN_KEYS = ['rcm_relevant', 'opportunity'] as const
const NUMBER_KEYS = ['score_min', 'score_max', 'page'] as const
const STRING_KEYS = [
  'q',
  'source',
  'problem_category',
  'payer',
  'specialty',
  'seeking_level',
  'speaker_type',
  'content_stance',
  'opportunity_type',
  'date_from',
  'date_to',
  'collected_from',
  'collected_to',
  'sort',
] as const

/** All Signals link that reproduces a KPI card / chart bucket exactly: the
 *  backend hands over the /api/posts filter, the Explorer passes it through. */
export function explorerHref(filter: DrillFilter): string {
  const params = new URLSearchParams()
  Object.entries(filter).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
  })
  const qs = params.toString()
  return qs ? `/explorer?${qs}` : '/explorer'
}

export function filtersFromParams(params: URLSearchParams): PostFilters {
  const f: PostFilters = {}
  const mutable = f as Record<string, unknown>
  BOOLEAN_KEYS.forEach((k) => {
    const v = params.get(k)
    if (v === 'true' || v === 'false') mutable[k] = v === 'true'
  })
  NUMBER_KEYS.forEach((k) => {
    const v = params.get(k)
    if (v !== null && v !== '' && !Number.isNaN(Number(v))) mutable[k] = Number(v)
  })
  STRING_KEYS.forEach((k) => {
    const v = params.get(k)
    if (v) mutable[k] = v
  })
  return f
}

export function paramsFromFilters(filters: PostFilters): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([k, v]) => {
    if (k === 'page_size') return
    if (k === 'page' && v === 1) return
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
  })
  return params
}

export function humanize(key: string): string {
  if (key === 'none') return 'Not seeking'
  return key.replaceAll('_', ' ').replace(/^./, (c) => c.toUpperCase())
}
