export interface ScoreBreakdown {
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
  page?: number
  page_size?: number
}
