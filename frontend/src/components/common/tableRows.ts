import { formatDate } from '@/utils/format'

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
