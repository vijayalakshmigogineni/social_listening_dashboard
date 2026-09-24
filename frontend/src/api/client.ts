import type {
  AnalysisJob,
  CollectionJob,
  CollectionJobRequest,
  CollectionSourcesResponse,
  PendingAnalysis,
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

/** FastAPI puts the reason in `detail` -- a string, or a list of validation errors. */
async function errorMessage(res: Response, path: string): Promise<string> {
  try {
    const body = await res.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d) => String(d.msg ?? d).replace(/^Value error, /, '')).join('; ')
    }
  } catch {
    // not JSON -- fall through to the status line
  }
  return `Request to ${path} failed: ${res.status} ${res.statusText}`
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(await errorMessage(res, path))
  }
  return res.json() as Promise<T>
}

async function postJson<T>(path: string, body: unknown = {}): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(await errorMessage(res, path))
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

  getCollectionSources: () => getJson<CollectionSourcesResponse>('/api/collection/sources'),
  startCollection: (req: CollectionJobRequest) =>
    postJson<CollectionJob>('/api/collection/jobs', req),
  getCollectionJob: (id: number) => getJson<CollectionJob>(`/api/collection/jobs/${id}`),
  listCollectionJobs: (limit = 20) =>
    getJson<{ results: CollectionJob[] }>(`/api/collection/jobs${buildQuery({ limit })}`),
  retryCollection: (id: number) => postJson<CollectionJob>(`/api/collection/jobs/${id}/retry`),

  getPendingAnalysis: () => getJson<PendingAnalysis>('/api/analysis/pending'),
  startAnalysis: (collectionJobId?: number) =>
    postJson<AnalysisJob>('/api/analysis/jobs', { collection_job_id: collectionJobId ?? null }),
  getAnalysisJob: (id: number) => getJson<AnalysisJob>(`/api/analysis/jobs/${id}`),
  listAnalysisJobs: (limit = 5) =>
    getJson<{ results: AnalysisJob[] }>(`/api/analysis/jobs${buildQuery({ limit })}`),
}
