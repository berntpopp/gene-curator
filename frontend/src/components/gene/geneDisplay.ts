/**
 * Priority display helpers for scope gene assignments.
 */
export function getPriorityColor(priority: string | null | undefined): string {
  const colors: Record<string, string> = {
    high: 'error',
    medium: 'warning',
    low: 'success'
  }
  return colors[priority ?? ''] ?? 'grey'
}

export function getPriorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    high: 'High',
    medium: 'Medium',
    low: 'Low'
  }
  return labels[priority] || priority
}
