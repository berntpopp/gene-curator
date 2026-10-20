/**
 * Display helpers for gene assignments (status / priority labels, colours and
 * due-date wording) used by GeneAssignmentManager.
 */

export interface SelectOption {
  title: string
  value: string
}

export const statusOptions: SelectOption[] = [
  { title: 'Unassigned', value: 'unassigned' },
  { title: 'Assigned', value: 'assigned' },
  { title: 'In Progress', value: 'in_progress' },
  { title: 'Under Review', value: 'under_review' },
  { title: 'Completed', value: 'completed' },
  { title: 'On Hold', value: 'on_hold' }
]

export const priorityOptions: SelectOption[] = [
  { title: 'Low', value: 'low' },
  { title: 'Medium', value: 'medium' },
  { title: 'High', value: 'high' },
  { title: 'Urgent', value: 'urgent' }
]

const STATUS_COLORS: Record<string, string> = {
  unassigned: 'grey',
  assigned: 'info',
  in_progress: 'primary',
  under_review: 'warning',
  completed: 'success',
  on_hold: 'orange'
}

const PRIORITY_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
  urgent: 'deep-purple'
}

export function getStatusColor(status: string): string {
  return STATUS_COLORS[status] ?? 'grey'
}

export function getPriorityColor(priority: string | null | undefined): string {
  return PRIORITY_COLORS[priority ?? ''] ?? 'grey'
}

/** snake_case status -> Title Case label */
export function formatStatus(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

/** Capitalise the first letter of a priority */
export function formatPriority(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1)
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString()
}

/** Whole days from now until the given date (negative when overdue) */
function daysUntil(dateString: string): number {
  const dueDate = new Date(dateString)
  const today = new Date()
  return Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

export function getDueDateClass(dateString: string): string {
  const diffDays = daysUntil(dateString)

  if (diffDays < 0) return 'text-error'
  if (diffDays < 7) return 'text-warning'
  return 'text-success'
}

export function getDueDateStatus(dateString: string): string {
  const diffDays = daysUntil(dateString)

  if (diffDays < 0) return `${Math.abs(diffDays)} days overdue`
  if (diffDays === 0) return 'Due today'
  if (diffDays === 1) return 'Due tomorrow'
  return `${diffDays} days remaining`
}
