/**
 * Display helpers for gene assignments (priority labels and colours) used by GeneAssignmentManager.
 */

export interface SelectOption {
  title: string
  value: string
}

export const priorityOptions: SelectOption[] = [
  { title: 'Low', value: 'low' },
  { title: 'Medium', value: 'medium' },
  { title: 'High', value: 'high' },
  { title: 'Urgent', value: 'urgent' }
]

const PRIORITY_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
  urgent: 'deep-purple'
}

export function getPriorityColor(priority: string | null | undefined): string {
  return PRIORITY_COLORS[priority ?? ''] ?? 'grey'
}

/** Capitalise the first letter of a priority */
export function formatPriority(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1)
}
