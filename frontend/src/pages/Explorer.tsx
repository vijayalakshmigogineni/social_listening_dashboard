import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Post, PostFilters } from '../api/types'
import { filtersFromParams, paramsFromFilters } from '../components/drill'
import { FilterBar } from '../components/FilterBar'
import { PostCard } from '../components/PostCard'

const PAGE_SIZE = 20

/** All Signals. The URL is the source of truth for filters, so Overview
 *  cards/charts can deep-link here and back/forward work. */
export function Explorer() {
  const [params, setParams] = useSearchParams()
  const filters = useMemo<PostFilters>(
    () => ({ sort: 'score_desc', page: 1, ...filtersFromParams(params), page_size: PAGE_SIZE }),
    [params],
  )
  const [results, setResults] = useState<Post[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    const timeout = setTimeout(() => {
      api
        .listPosts(filters)
        .then((r) => {
          setResults(r.results)
          setTotal(r.total)
          setError(null)
        })
        .catch((e) => setError(String(e)))
        .finally(() => setLoading(false))
    }, 250) // debounce keyword typing
    return () => clearTimeout(timeout)
  }, [filters])

  const setFilters = (next: PostFilters) => setParams(paramsFromFilters(next))
  const page = filters.page ?? 1
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="explorer">
      <h2>All Signals</h2>
      <FilterBar filters={filters} onChange={setFilters} />

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading">Loading...</div>}

      <div className="result-count">
        {total} result{total === 1 ? '' : 's'}
      </div>

      <div className="post-grid">
        {results.map((p) => (
          <PostCard key={`${p.source}:${p.source_item_id}`} post={p} />
        ))}
      </div>

      <div className="pagination">
        <button disabled={page <= 1} onClick={() => setFilters({ ...filters, page: page - 1 })}>
          Previous
        </button>
        <span>
          Page {page} of {pageCount}
        </span>
        <button disabled={page >= pageCount} onClick={() => setFilters({ ...filters, page: page + 1 })}>
          Next
        </button>
      </div>
    </div>
  )
}
