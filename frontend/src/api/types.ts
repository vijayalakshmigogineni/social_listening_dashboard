/** ProbePS opportunity score: three components normalized to 0-100 and
 *  weighted 65% LLM assessment + 20% RCM relevance + 15% Step 3 specificity.
 *  Mirrors backend ScoreBreakdownOpportunity (app/schemas/analysis.py). */
export interface LlmPoints {
  problem_evidence: number
  first_person: number
  seeking: number
  business_impact: number
  recurring: number
  probeps_fit: number
}

export interface RcmPoints {
  relevance: number
  category_severity: number
  primary_problem_category: string | null
}

export interface Step3Points {
  category: number
  payer: number
  procedure: number
  denial_reason: number
  code: number
  specialty: number
  total: number
}

export type Grade = 'none' | 'low' | 'moderate' | 'high'

/** The persisted Step 2 LLM output (score_breakdown.llm_assessment). */
export interface LlmAssessment {
  problem_evidence: boolean
  problem_current: boolean
  problem_recurring: boolean
  first_person: boolean
  operational_impact: boolean
  speaker_type: string
  content_stance: string
  seeking_level: string | null
  evidence_quote: string | null
  pain_severity: Grade | null
  business_impact: Grade | null
  probeps_fit: Grade | null
  opportunity_type: string | null
  opportunity_reasoning: string | null
  problem_confidence: number
  first_person_confidence: number | null
  seeking_confidence: number | null
  pain_confidence: number | null
  impact_confidence: number | null
  fit_confidence: number | null
  semantic_source: 'llm' | 'fallback'
}

export interface ScoreBreakdown {
  llm_score: number
  rcm_score: number
  step3_score: number
  weights: { llm: number; rcm: number; step3: number }
  llm_contribution: number
  rcm_contribution: number
  step3_contribution: number
  llm_points: LlmPoints
  rcm_points: RcmPoints
  step3_points: Step3Points
  llm_cap_applied: boolean
  cap_applied: boolean
  cap_reason: string | null
  pre_cap_score: number
  final_score: number
  llm_source: 'llm' | 'fallback' | null
  llm_assessment: LlmAssessment | null
}

/** True for rows scored by the current opportunity scorer (older analysis
 *  versions stored a different breakdown shape). */
export function isOpportunityBreakdown(b: unknown): b is ScoreBreakdown {
  return typeof b === 'object' && b !== null && 'llm_score' in b && 'weights' in b
}
export interface Post {
  source: string
  source_item_id: string
  url: string | null
  title: string | null
  text: string | null
  author_id: string | null
  author_name: string | null
  author_profile_url: string | null
  author_role: string | null
  organization_name: string | null
  organization_url: string | null
  location: string | null
  created_at: string | null
  collected_at: string | null
  engagement: Record<string, unknown> | null
  parent_id: string | null
  conversation_id: string | null
  media_type: string | null
  source_metadata: Record<string, unknown> | null

  analyzed: boolean
  rcm_relevant: boolean | null
  problem_evidence: boolean | null
  problem_category: string[]
  payer_tags: string[]
  procedure_tags: string[]
  denial_reason_tags: string[]
  specialty: string | null
  speaker_type: string | null
  content_stance: string | null
  seeking_level: string | null
  evidence_quote: string | null
  confidence: number | null
  final_score: number | null
  llm_score: number | null
  rcm_score: number | null
  step3_score: number | null
  opportunity_type: string | null
  probeps_fit: Grade | null
  opportunity_reasoning: string | null
  is_opportunity: boolean
  score_breakdown: ScoreBreakdown | null
  analysis_version: string | null
  scoring_version: string | null
}

export interface PostListResponse {
  total: number
  page: number
  page_size: number
  results: Post[]
}

/** An /api/posts filter that reproduces a KPI card or chart bucket. */
export type DrillFilter = Partial<Record<keyof PostFilters, string | number | boolean>>

export interface Kpi {
  value: number
  filter: DrillFilter
}

export interface Bucket {
  key: string
  count: number
  filter: DrillFilter
}

export interface OverviewResponse {
  kpis: {
    total_opportunities: Kpi
    new_today: Kpi
    rcm_relevant: Kpi
  }
  series: {
    opportunities_over_time: { bucket: 'day' | 'week' | 'month'; points: Bucket[]; earlier: number; undated: number }
    problem_category: Bucket[]
    source_contribution: Bucket[]
    seeking_level: Bucket[]
  }
  top: Post[]
  definitions: {
    opportunity_threshold: number
    opportunity_rule: string
    new_today_rule: string
    rcm_relevant_rule: string
    report_tz: string
    today_start: string
    analysis_version: string
  }
}

export interface PipelineExplanation {
  mode: 'stored' | 'live'
  analyzed: boolean
  raw_record: Record<string, unknown>
  normalized_record: Record<string, unknown>
  input_text: string
  analysis_version: string
  scoring_version: string | null
  step1_rcm_relevance?: Record<string, unknown>
  step3_taxonomy?: Record<string, unknown>
  step5_evidence_confidence?: Record<string, unknown>
  /** live mode only: the full per-stage trace */
  parent_text?: string | null
  step2_semantic?: Record<string, unknown> | null
  step2_problem_evidence?: Record<string, unknown>
  step4_context?: Record<string, unknown>
  score_breakdown: ScoreBreakdown | Record<string, unknown> | null
  final_score: number | null
}

export interface PostFilters {
  q?: string
  source?: string
  problem_category?: string
  payer?: string
  specialty?: string
  seeking_level?: string
  speaker_type?: string
  content_stance?: string
  rcm_relevant?: boolean
  opportunity?: boolean
  opportunity_type?: string
  score_min?: number
  score_max?: number
  date_from?: string
  date_to?: string
  collected_from?: string
  collected_to?: string
  sort?: 'score_desc' | 'score_asc' | 'recent' | 'oldest'
  page?: number
  page_size?: number
}
// --- Data Collection / Analysis jobs ---------------------------------------

export type CollectionMode = 'since_last_sweep' | 'custom_range' | 'latest_n'

export type JobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'completed_with_errors'
  | 'failed'
  | 'interrupted'

export type SourceRunStatus = 'waiting' | 'fetching' | 'completed' | 'partial' | 'failed'

export interface SourceCheckpoint {
  last_successful_fetch: string | null
  last_job_id: number | null
  next_sweep_from: string | null
  next_sweep_from_origin: 'checkpoint' | 'newest_stored_post' | 'default_lookback'
}

export interface CollectionSource {
  key: string
  label: string
  available: boolean
  unavailable_reason: string | null
  unit_label: string
  units: string[]
  /** Editable rows behind `units` (the saved list, or the collector default). */
  unit_values: SourceUnit[]
  /** True when the page saved its own list instead of the default. */
  customized: boolean
  unit_rule: SourceUnitRule
  sweep_depth_per_unit: number
  cost_note: string
  checkpoint: SourceCheckpoint
}

export interface SourceUnit {
  name: string
  value: string
}

export interface SourceUnitRule {
  value_label: string
  value_hint: string
  /** Named units carry their own short name; unnamed ones derive it from the value. */
  named: boolean
  max_units: number
}

export interface SourceStat {
  posts: number
  analyzed: number
  pending: number
  rcm_relevant: number
  opportunities: number
  last_collected_at: string | null
  newest_post_at: string | null
  collected_per_day: number[]
}

export interface SourceStatsResponse {
  days: string[]
  sources: Record<string, SourceStat>
}

export interface ActiveJob {
  kind: 'collection' | 'analysis'
  id: number | null
}

export interface CollectionSourcesResponse {
  max_post_limit: number
  sources: CollectionSource[]
  active_job: ActiveJob | null
}

export interface SourceRunResult {
  status: SourceRunStatus
  fetched: number
  new: number
  duplicate: number
  skipped: number
  units_total: number
  units_done: number
  current_unit: string | null
  window_start: string | null
  window_end: string | null
  window_origin: string | null
  depth_per_unit: number | null
  errors: string[]
  warnings: string[]
  checkpoint_advanced: boolean
  started_at: string | null
  completed_at: string | null
}

export interface CollectionJob {
  id: number
  mode: CollectionMode
  sources: string[]
  start_date: string | null
  end_date: string | null
  post_limit: number | null
  status: JobStatus
  posts_fetched: number
  posts_new: number
  posts_duplicate: number
  posts_skipped: number
  source_results: Record<string, SourceRunResult>
  errors: string[]
  retry_of: number | null
  retryable_sources: string[]
  created_at: string
  started_at: string | null
  completed_at: string | null
  duration_s: number | null
}

export interface CollectionJobRequest {
  mode: CollectionMode
  sources: string[]
  start_date?: string
  end_date?: string
  post_limit?: number
}

export interface AnalysisJob {
  id: number
  source: string | null
  collection_job_id: number | null
  status: JobStatus
  total_posts: number
  processed_posts: number
  failed_posts: number
  current_stage: string | null
  current_stage_number: number | null
  stages: string[]
  errors: string[]
  scores: { score?: number[] }
  created_at: string
  started_at: string | null
  completed_at: string | null
  duration_s: number | null
}

export interface PendingAnalysis {
  pending_posts: number
  active_job: ActiveJob | null
}
