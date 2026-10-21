import { computed, onScopeDispose, ref, watch } from 'vue'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'

export type Density = 'compact' | 'comfortable'
export interface SortItem {
  key: string
  order: 'asc' | 'desc'
}
export type FilterValue = string | string[]

export const PAGE_SIZES = [10, 25, 50, 100]
const DEFAULT_SIZE = 25
const DEFAULT_DENSITY: Density = 'comfortable'
const RESERVED = ['q', 'page', 'size', 'sort', 'order', 'density']
const SEARCH_DEBOUNCE_MS = 300

type Patch = Record<string, LocationQuery[string] | undefined>
// Shared by all instances: writes in one tick merge, so one table never drops another's keys
// (router.replace is async and each flush must start from the latest query).
let pending: Patch | null = null

/**
 * Table state (search, filters, sort, page, size, density) kept in the URL query so a reload
 * or shared link restores it. Defaults are omitted; any change except `page` and `density`
 * resets to page 1. `prefix` ("review" -> `review.page`) lets several tables share one route.
 * Keys in `multiKeys` are multi-select filters stored as repeated query keys.
 */
export function useTableUrlState(
  opts: { filterKeys?: string[]; multiKeys?: string[]; pageSize?: number; prefix?: string } = {}
) {
  const route = useRoute()
  const router = useRouter()
  const filterKeys = opts.filterKeys ?? []
  const multiKeys = opts.multiKeys ?? []
  const defaultSize = opts.pageSize ?? DEFAULT_SIZE
  const clash = filterKeys.find(k => RESERVED.includes(k))
  if (clash) throw new Error(`filterKeys: "${clash}" is a reserved key`)

  const key = (k: string) => (opts.prefix ? `${opts.prefix}.${k}` : k)
  const all = (k: string): string[] => {
    const v = route.query[key(k)]
    return (Array.isArray(v) ? v : [v]).filter((x): x is string => !!x)
  }
  const str = (k: string): string | undefined => all(k)[0]
  const posInt = (k: string, fallback: number): number => {
    const n = Number(str(k))
    return Number.isSafeInteger(n) && n > 0 ? n : fallback
  }

  function write(patch: Patch, keepPage = false) {
    if (!pending) {
      const batch: Patch = (pending = {})
      queueMicrotask(() => {
        pending = null
        const merged: Patch = { ...route.query, ...batch }
        for (const k of Object.keys(merged)) if (!merged[k]?.length) delete merged[k]
        void router.replace({ query: merged as LocationQuery })
      })
    }
    const prefixed = Object.fromEntries(Object.entries(patch).map(([k, v]) => [key(k), v]))
    Object.assign(
      pending,
      prefixed,
      keepPage || 'page' in patch ? {} : { [key('page')]: undefined }
    )
  }

  // Typed text lives locally so the field is not reset while the debounced URL write is pending.
  const typed = ref(str('q') ?? '')
  let timer: ReturnType<typeof setTimeout> | undefined
  watch(
    () => str('q'),
    q => {
      clearTimeout(timer)
      typed.value = q ?? ''
    }
  )
  onScopeDispose(() => clearTimeout(timer))
  const search = computed({
    get: () => typed.value,
    set: v => {
      typed.value = v
      clearTimeout(timer)
      timer = setTimeout(() => write({ q: v || undefined }), SEARCH_DEBOUNCE_MS)
    }
  })
  const page = computed({
    get: () => posInt('page', 1),
    set: v => write({ page: v > 1 ? String(v) : undefined })
  })
  const itemsPerPage = computed({
    get: () => {
      const n = posInt('size', defaultSize)
      return PAGE_SIZES.includes(n) ? n : defaultSize
    },
    set: v => write({ size: v === defaultSize ? undefined : String(v) })
  })
  const sortBy = computed<SortItem[]>({
    get: () => {
      const k = str('sort')
      return k
        ? [{ key: k, order: (str('order') === 'desc' ? 'desc' : 'asc') as SortItem['order'] }]
        : []
    },
    set: v => write({ sort: v[0]?.key, order: v[0]?.order })
  })
  const density = computed<Density>({
    get: () => (str('density') === 'compact' ? 'compact' : DEFAULT_DENSITY),
    // Density is a view preference, not a data filter: keep the current page.
    set: v => write({ density: v === DEFAULT_DENSITY ? undefined : v }, true)
  })
  const filters = computed<Record<string, FilterValue>>({
    get: () =>
      Object.fromEntries(
        filterKeys.flatMap(k => {
          const v = all(k)
          return v.length ? [[k, multiKeys.includes(k) ? v : v[0]]] : []
        })
      ) as Record<string, FilterValue>,
    set: v => write(Object.fromEntries(filterKeys.map(k => [k, v[k] || undefined])))
  })

  return { search, page, itemsPerPage, sortBy, density, filters }
}
