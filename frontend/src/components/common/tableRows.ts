import { formatDate } from '@/utils/format'
import type { SortItem } from '@/composables/useTableUrlState'

/** "3d ago" within a week, then the date; for list rows where age matters more than the day. */
export function relativeTime(value: string | null | undefined, now = Date.now()): string {
  if (!value) return 'unknown'
  const min = Math.floor((now - new Date(value).getTime()) / 60000)
  const hours = Math.floor(min / 60)
  const days = Math.floor(hours / 24)
  if (days > 7) return formatDate(value)
  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  if (min > 0) return `${min}m ago`
  return 'just now'
}

/**
 * Sort and page a list held in full on the client, for DataTable (a server table) over it.
 * ponytail: fine for a user's own queue; move to server paging if a list grows past a few thousand.
 */
export function clientPage<T extends object>(
  rows: T[],
  opts: { sortBy: SortItem[]; page: number; itemsPerPage: number }
): T[] {
  const s = opts.sortBy[0]
  const sorted = s
    ? [...rows].sort((a, b) => {
        const x = (a as Record<string, unknown>)[s.key]
        const y = (b as Record<string, unknown>)[s.key]
        const cmp =
          typeof x === 'number' && typeof y === 'number'
            ? x - y
            : String(x ?? '').localeCompare(String(y ?? ''))
        return s.order === 'desc' ? -cmp : cmp
      })
    : rows
  const start = (opts.page - 1) * opts.itemsPerPage
  return sorted.slice(start, start + opts.itemsPerPage)
}
