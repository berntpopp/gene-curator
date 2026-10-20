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
