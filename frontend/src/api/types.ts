export interface ScoreBreakdownV1 {
  problem_strength: number
  market_relevance: number
  intent_strength: number
  specificity: number
  severity: number
  base_score: number
  confidence: number
  recency_factor: number
  final_score: number
}

/** v2: additive components, then multiplicative factors (1.0 = did not apply). */
export interface ScoreBreakdownV2 {
  problem_strength: number
  identity: number
  specificity: number
  intent_strength: number
  interaction_bonus: number
  base_score: number
  relevance_factor: number
  domain_factor: number
  commentary_factor: number
  noise_factor: number
  offdomain_factor: number
  final_score: number
  signals: string[]
}

export type ScoreBreakdown = ScoreBreakdownV1 | ScoreBreakdownV2

export function isV2Breakdown(b: ScoreBreakdown): b is ScoreBreakdownV2 {
  return 'relevance_factor' in b
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

export interface Summary {
  total_posts: number
  total_analyzed: number
  total_rcm_relevant: number
  total_problem_evidence: number
  avg_score: number | null
  by_source: Record<string, number>
  by_seeking_level: Record<string, number>
  by_speaker_type: Record<string, number>
  by_problem_category: Record<string, number>
  analysis_version: string
}

export interface PipelineExplanation {
  raw_record: Record<string, unknown>
  normalized_record: Record<string, unknown>
  input_text: string
  step1_rcm_relevance: Record<string, unknown>
  step2_problem_evidence: Record<string, unknown>
  step3_taxonomy: Record<string, unknown>
  step4_context: Record<string, unknown>
  step5_evidence_confidence: Record<string, unknown>
  step6_7_scoring: ScoreBreakdown
  analysis_version: string
  scoring_version: string
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
  score_min?: number
  score_max?: number
  sort?: 'score_desc' | 'score_asc' | 'recent' | 'oldest'
  version?: ScoringVersion
  page?: number
  page_size?: number
}

/** Which stored scoring version the dashboard reads. Both are persisted per
 *  post, so switching this re-ranks the whole dashboard without re-analysing. */
export type ScoringVersion = 'v1' | 'v2'

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
  sweep_depth_per_unit: number
  cost_note: string
  checkpoint: SourceCheckpoint
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
  scores: { v1?: number[]; v2?: number[] }
  created_at: string
  started_at: string | null
  completed_at: string | null
  duration_s: number | null
}

export interface PendingAnalysis {
  pending_posts: number
  active_job: ActiveJob | null
}
