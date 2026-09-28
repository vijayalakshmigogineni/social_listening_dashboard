import type { PostFilters } from '../api/types'
import { humanize } from './drill'

interface Props {
  filters: PostFilters
  onChange: (filters: PostFilters) => void
}

const CATEGORIES = [
  'authorization_utilization_management',
  'denials_claims_friction',
  'coverage_policy',
  'documentation_medical_necessity',
  'reimbursement_payment',
  'procedure_device_access',
]

const SEEKING_LEVELS = ['L0', 'L1', 'L2', 'L3']
const SPEAKER_TYPES = ['practice_side', 'patient', 'payer_side', 'vendor', 'educator_media', 'unknown']
const STANCES = ['seeking', 'supplying', 'neutral', 'mixed']
const SOURCES = ['reddit', 'aapc', 'linkedin', 'facebook', 'x', 'youtube']
const OPPORTUNITY_TYPES = [
  'denial_management',
  'prior_authorization',
  'ar_followup_cashflow',
  'coding_documentation',
  'payer_policy_reimbursement',
  'billing_operations_staffing',
  'informational_only',
  'not_an_opportunity',
]

function formatWhen(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

/** Filters set by an Overview drill-down that have no control of their own
 *  here -- shown as removable chips so the active view is never hidden. */
function activeChips(filters: PostFilters): { key: keyof PostFilters; text: string }[] {
  const chips: { key: keyof PostFilters; text: string }[] = []
  if (filters.date_from) chips.push({ key: 'date_from', text: `Posted from ${formatWhen(filters.date_from)}` })
  if (filters.date_to) chips.push({ key: 'date_to', text: `Posted to ${formatWhen(filters.date_to)}` })
  if (filters.collected_from) chips.push({ key: 'collected_from', text: `Collected from ${formatWhen(filters.collected_from)}` })
  if (filters.collected_to) chips.push({ key: 'collected_to', text: `Collected to ${formatWhen(filters.collected_to)}` })
  if (filters.payer) chips.push({ key: 'payer', text: `Payer: ${filters.payer}` })
  if (filters.specialty) chips.push({ key: 'specialty', text: `Specialty: ${filters.specialty}` })
  if (filters.score_max !== undefined) chips.push({ key: 'score_max', text: `Max score ${filters.score_max}` })
  return chips
}

export function FilterBar({ filters, onChange }: Props) {
  const set = (patch: Partial<PostFilters>) => onChange({ ...filters, ...patch, page: 1 })
  const chips = activeChips(filters)

  return (
    <>
    <div className="filter-bar">
      <select
        value={filters.opportunity === undefined ? '' : String(filters.opportunity)}
        onChange={(e) => set({ opportunity: e.target.value === '' ? undefined : e.target.value === 'true' })}
      >
        <option value="">All signals</option>
        <option value="true">Opportunities only</option>
        <option value="false">Non-opportunities</option>
      </select>

      <select
        value={filters.rcm_relevant === undefined ? '' : String(filters.rcm_relevant)}
        onChange={(e) => set({ rcm_relevant: e.target.value === '' ? undefined : e.target.value === 'true' })}
      >
        <option value="">Any RCM relevance</option>
        <option value="true">RCM relevant</option>
        <option value="false">Not RCM relevant</option>
      </select>

      <select
        value={filters.opportunity_type ?? ''}
        onChange={(e) => set({ opportunity_type: e.target.value || undefined })}
      >
        <option value="">Any opportunity type</option>
        {OPPORTUNITY_TYPES.map((t) => (
          <option key={t} value={t}>
            {humanize(t)}
          </option>
        ))}
      </select>

      <input
        type="text"
        placeholder="Search keyword, payer, category..."
        value={filters.q ?? ''}
        onChange={(e) => set({ q: e.target.value })}
        className="filter-search"
      />

      <select value={filters.source ?? ''} onChange={(e) => set({ source: e.target.value || undefined })}>
        <option value="">All sources</option>
        {SOURCES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <select
        value={filters.problem_category ?? ''}
        onChange={(e) => set({ problem_category: e.target.value || undefined })}
      >
        <option value="">All categories</option>
        {CATEGORIES.map((c) => (
          <option key={c} value={c}>
            {c.replaceAll('_', ' ')}
          </option>
        ))}
      </select>

      <select
        value={filters.seeking_level ?? ''}
        onChange={(e) => set({ seeking_level: e.target.value || undefined })}
      >
        <option value="">Any seeking level</option>
        {SEEKING_LEVELS.map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
        <option value="none">Not seeking</option>
      </select>

      <select
        value={filters.speaker_type ?? ''}
        onChange={(e) => set({ speaker_type: e.target.value || undefined })}
      >
        <option value="">Any speaker</option>
        {SPEAKER_TYPES.map((s) => (
          <option key={s} value={s}>
            {s.replaceAll('_', ' ')}
          </option>
        ))}
      </select>

      <select
        value={filters.content_stance ?? ''}
        onChange={(e) => set({ content_stance: e.target.value || undefined })}
      >
        <option value="">Any stance</option>
        {STANCES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <input
        type="number"
        placeholder="Min score"
        value={filters.score_min ?? ''}
        onChange={(e) => set({ score_min: e.target.value ? Number(e.target.value) : undefined })}
        className="filter-number"
      />

      <select value={filters.sort ?? 'score_desc'} onChange={(e) => set({ sort: e.target.value as PostFilters['sort'] })}>
        <option value="score_desc">Highest score</option>
        <option value="score_asc">Lowest score</option>
        <option value="recent">Most recent</option>
        <option value="oldest">Oldest</option>
      </select>
    </div>
    {chips.length > 0 && (
      <div className="filter-chips">
        {chips.map((chip) => (
          <button key={chip.key} className="filter-chip" onClick={() => set({ [chip.key]: undefined })}>
            {chip.text} <span aria-hidden="true">×</span>
            <span className="sr-only">remove filter</span>
          </button>
        ))}
      </div>
    )}
    </>
  )
}
