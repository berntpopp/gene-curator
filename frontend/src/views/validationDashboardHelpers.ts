const STATUS_COLORS: Record<string, string> = {
  valid: 'success',
  invalid: 'error',
  warning: 'warning',
  pending: 'info'
}

const STATUS_ICONS: Record<string, string> = {
  valid: 'mdi-check',
  invalid: 'mdi-close',
  warning: 'mdi-alert',
  pending: 'mdi-clock'
}

const SEVERITY_COLORS: Record<string, string> = {
  error: 'error',
  warning: 'warning',
  info: 'info'
}

export const getValidationStatusColor = (status: string): string => STATUS_COLORS[status] || 'grey'

export const getValidationStatusIcon = (status: string): string =>
  STATUS_ICONS[status] || 'mdi-help'

export const getSeverityColor = (severity: string): string => SEVERITY_COLORS[severity] || 'grey'

export const formatValidationStatus = (status: string): string =>
  status.charAt(0).toUpperCase() + status.slice(1)

export const formatDate = (dateString: string | null | undefined): string =>
  dateString ? new Date(dateString).toLocaleDateString() : 'N/A'

export const getTimeAgo = (dateString: string | null | undefined, now = new Date()): string => {
  if (!dateString) return ''
  const diffMs = now.getTime() - new Date(dateString).getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffHours < 1) return 'Just now'
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return 'Over a week ago'
}
