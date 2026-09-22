import type { PostFilters } from '../api/types'

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
const SOURCES = ['reddit', 'aapc', 'linkedin']

export function FilterBar({ filters, onChange }: Props) {
  const set = (patch: Partial<PostFilters>) => onChange({ ...filters, ...patch, page: 1 })

  return (
    <div className="filter-bar">
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
  )
}
