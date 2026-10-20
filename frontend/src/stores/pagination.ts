/** Page-style pagination state the list views bind to. */
export interface PageState {
  page: number
  per_page: number
  total: number
  pages: number
}

/** Derive page-style state from the backend's skip/limit list envelope. */
export function pageStateFrom(r: { total: number; skip: number; limit: number }): PageState {
  const perPage = r.limit > 0 ? r.limit : 1
  return {
    page: Math.floor(r.skip / perPage) + 1,
    per_page: r.limit,
    total: r.total,
    pages: Math.ceil(r.total / perPage)
  }
}
