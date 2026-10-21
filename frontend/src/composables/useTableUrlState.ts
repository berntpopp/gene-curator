import { computed } from 'vue'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'

export type Density = 'compact' | 'comfortable'
export interface SortItem {
  key: string
  order: 'asc' | 'desc'
}

const DEFAULT_SIZE = 25
const DEFAULT_DENSITY: Density = 'comfortable'

/**
 * Table state (search, filters, sort, page, size, density) kept in the URL query so a reload
 * or shared link restores it. Defaults are omitted; any change except `page` resets to page 1.
 */
export function useTableUrlState(opts: { filterKeys?: string[]; pageSize?: number } = {}) {
  const route = useRoute()
  const router = useRouter()
  const filterKeys = opts.filterKeys ?? []
  const defaultSize = opts.pageSize ?? DEFAULT_SIZE

  const str = (k: string): string | undefined => {
    const v = route.query[k]
    return (Array.isArray(v) ? v[0] : v) || undefined
  }
  const posInt = (k: string, fallback: number): number => {
    const n = Number(str(k))
    return Number.isInteger(n) && n > 0 ? n : fallback
  }

  // Writes in one tick are merged, otherwise each would overwrite the previous (replace is async).
  let pending: Record<string, string | undefined> | null = null
  function write(patch: Record<string, string | undefined>, keepPage = false) {
    if (!pending) {
      pending = {}
      queueMicrotask(() => {
        const merged: Record<string, LocationQuery[string] | undefined> = {
          ...route.query,
          ...pending
        }
        pending = null
        for (const k of Object.keys(merged)) if (!merged[k]) delete merged[k]
        void router.replace({ query: merged as LocationQuery })
      })
    }
    Object.assign(pending, patch, keepPage || 'page' in patch ? {} : { page: undefined })
  }

  const search = computed({
    get: () => str('q') ?? '',
    set: v => write({ q: v || undefined })
  })
  const page = computed({
    get: () => posInt('page', 1),
    set: v => write({ page: v > 1 ? String(v) : undefined })
  })
  const itemsPerPage = computed({
    get: () => posInt('size', defaultSize),
    set: v => write({ size: v === defaultSize ? undefined : String(v) })
  })
  const sortBy = computed<SortItem[]>({
    get: () => {
      const key = str('sort')
      return key
        ? [{ key, order: (str('order') === 'desc' ? 'desc' : 'asc') as SortItem['order'] }]
        : []
    },
    set: v => write({ sort: v[0]?.key, order: v[0]?.order })
  })
  const density = computed<Density>({
    get: () => (str('density') === 'compact' ? 'compact' : DEFAULT_DENSITY),
    // Density is a view preference, not a data filter: keep the current page.
    set: v => write({ density: v === DEFAULT_DENSITY ? undefined : v }, true)
  })
  const filters = computed<Record<string, string>>({
    get: () =>
      Object.fromEntries(filterKeys.flatMap(k => (str(k) ? [[k, str(k)]] : []))) as Record<
        string,
        string
      >,
    set: v => write(Object.fromEntries(filterKeys.map(k => [k, v[k] || undefined])))
  })

  return { search, page, itemsPerPage, sortBy, density, filters }
}
