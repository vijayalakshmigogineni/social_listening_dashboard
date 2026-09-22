import type { PipelineExplanation, Post, PostFilters, PostListResponse, Summary } from './types'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`Request to ${path} failed: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

function buildQuery(filters: PostFilters): string {
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
  listPosts: (filters: PostFilters) => getJson<PostListResponse>(`/api/posts${buildQuery(filters)}`),
  getPost: (source: string, sourceItemId: string) =>
    getJson<Post>(`/api/posts/${encodeURIComponent(source)}/${encodeURIComponent(sourceItemId)}`),
  getSummary: () => getJson<Summary>('/api/stats/summary'),
  explainPipeline: (source: string, sourceItemId: string) =>
    getJson<PipelineExplanation>(
      `/api/pipeline/${encodeURIComponent(source)}/${encodeURIComponent(sourceItemId)}`,
    ),
}
