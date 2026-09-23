import type {
  PipelineExplanation,
  Post,
  PostFilters,
  PostListResponse,
  ScoringVersion,
  Summary,
} from './types'

/**
 * Which scoring version the dashboard reads.
 *
 * Both v1 and v2 rows are stored for every post, so this is a read-time choice
 * -- flipping it re-ranks the entire dashboard with no re-analysis. v2 is the
 * model derived from the 167-post gold set; v1 is kept for comparison.
 */
export const SCORING_VERSION: ScoringVersion = 'v2'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`Request to ${path} failed: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

function buildQuery(filters: Record<string, unknown>): string {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  })
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  listPosts: (filters: PostFilters) =>
    getJson<PostListResponse>(
      `/api/posts${buildQuery({ version: SCORING_VERSION, ...filters })}`,
    ),
  getPost: (source: string, sourceItemId: string) =>
    getJson<Post>(
      `/api/posts/${encodeURIComponent(source)}/${encodeURIComponent(sourceItemId)}` +
        buildQuery({ version: SCORING_VERSION }),
    ),
  getSummary: () => getJson<Summary>(`/api/stats/summary${buildQuery({ version: SCORING_VERSION })}`),
  explainPipeline: (source: string, sourceItemId: string) =>
    getJson<PipelineExplanation>(
      `/api/pipeline/${encodeURIComponent(source)}/${encodeURIComponent(sourceItemId)}`,
    ),
}
