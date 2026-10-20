/**
 * Display helpers for scope gene assignments (GeneList and its card/row children).
 */

/** Progress percentage implied by an assignment status. */
export function calculateProgress(assignment: { status?: string | null }): number {
  const statusProgress: Record<string, number> = {
    assigned: 0,
    in_progress: 25,
    under_review: 75,
    completed: 100
  }
  return statusProgress[assignment.status ?? ''] || 0
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    assigned: 'grey',
    in_progress: 'warning',
    under_review: 'info',
    completed: 'success'
  }
  return colors[status] || 'grey'
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    assigned: 'Assigned',
    in_progress: 'In Progress',
    under_review: 'Under Review',
    completed: 'Completed'
  }
  return labels[status] || status
}

export function getPriorityColor(priority: string): string {
  const colors: Record<string, string> = {
    high: 'error',
    medium: 'warning',
    normal: 'warning',
    low: 'grey'
  }
  return colors[priority] || 'grey'
}

export function getPriorityIcon(priority: string): string {
  const icons: Record<string, string> = {
    high: 'mdi-flag',
    medium: 'mdi-flag',
    normal: 'mdi-flag',
    low: 'mdi-flag-outline'
  }
  return icons[priority] || 'mdi-flag-outline'
}

export function getPriorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    high: 'High',
    medium: 'Medium',
    normal: 'Medium',
    low: 'Low'
  }
  return labels[priority] || priority
}

export function getProgressColor(progress: number | null | undefined): string {
  if (progress !== null && progress !== undefined) {
    if (progress >= 75) return 'success'
    if (progress >= 50) return 'info'
    if (progress >= 25) return 'warning'
  }
  return 'grey'
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString()
}
