import type {
  AnalysisJob,
  CollectionJob,
  CollectionJobRequest,
  CollectionSource,
  CollectionSourcesResponse,
  PendingAnalysis,
  PipelineExplanation,
  Post,
  PostFilters,
  OverviewResponse,
  PostListResponse,
  SourceStatsResponse,
  SourceUnit,
} from './types'

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

async function postJson<T>(path: string, body: unknown = {}, method = 'POST'): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(await errorMessage(res, path))
  }
  return res.json() as Promise<T>
}

export function buildQuery(filters: Record<string, unknown>): string {
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
      `/api/posts${buildQuery({ ...filters })}`,
    ),
  getPost: (source: string, sourceItemId: string) =>
    getJson<Post>(`/api/posts/${encodeURIComponent(source)}/${encodeURIComponent(sourceItemId)}`),
  getOverview: (bucket: 'day' | 'week' | 'month' = 'month') =>
    getJson<OverviewResponse>(`/api/stats/overview${buildQuery({ bucket })}`),
  /** Stored breakdown by default; live=true re-runs every stage (calls the LLM). */
  explainPipeline: (source: string, sourceItemId: string, live = false) =>
    getJson<PipelineExplanation>(
      `/api/pipeline/${encodeURIComponent(source)}/${encodeURIComponent(sourceItemId)}` +
        buildQuery({ live: live || undefined }),
    ),

  getCollectionSources: () => getJson<CollectionSourcesResponse>('/api/collection/sources'),
  startCollection: (req: CollectionJobRequest) =>
    postJson<CollectionJob>('/api/collection/jobs', req),
  getCollectionJob: (id: number) => getJson<CollectionJob>(`/api/collection/jobs/${id}`),
  listCollectionJobs: (limit = 20) =>
    getJson<{ results: CollectionJob[] }>(`/api/collection/jobs${buildQuery({ limit })}`),
  retryCollection: (id: number) => postJson<CollectionJob>(`/api/collection/jobs/${id}/retry`),
  getSourceStats: () => getJson<SourceStatsResponse>('/api/collection/source-stats'),
  saveSourceUnits: (key: string, units: SourceUnit[]) =>
    postJson<CollectionSource>(`/api/collection/sources/${encodeURIComponent(key)}/units`, { units }, 'PUT'),
  resetSourceUnits: (key: string) =>
    postJson<CollectionSource>(`/api/collection/sources/${encodeURIComponent(key)}/units`, undefined, 'DELETE'),

  getPendingAnalysis: () => getJson<PendingAnalysis>('/api/analysis/pending'),
  startAnalysis: (collectionJobId?: number) =>
    postJson<AnalysisJob>('/api/analysis/jobs', { collection_job_id: collectionJobId ?? null }),
  getAnalysisJob: (id: number) => getJson<AnalysisJob>(`/api/analysis/jobs/${id}`),
  listAnalysisJobs: (limit = 5) =>
    getJson<{ results: AnalysisJob[] }>(`/api/analysis/jobs${buildQuery({ limit })}`),
}
