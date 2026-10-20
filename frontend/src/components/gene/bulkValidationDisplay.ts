/**
 * Display helpers for bulk gene validation statuses (AddGeneModal).
 */

export type BulkValidationStatus = 'valid' | 'suggestion' | 'not_found' | string

export function getValidationClass(status: BulkValidationStatus): string {
  switch (status) {
    case 'valid':
      return 'bg-success-lighten-5'
    case 'suggestion':
      return 'bg-warning-lighten-5'
    case 'not_found':
      return 'bg-error-lighten-5'
    default:
      return ''
  }
}

export function getValidationColor(status: BulkValidationStatus): string {
  switch (status) {
    case 'valid':
      return 'success'
    case 'suggestion':
      return 'warning'
    case 'not_found':
      return 'error'
    default:
      return 'grey'
  }
}

export function getValidationIcon(status: BulkValidationStatus): string {
  switch (status) {
    case 'valid':
      return 'mdi-check-circle'
    case 'suggestion':
      return 'mdi-help-circle'
    case 'not_found':
      return 'mdi-close-circle'
    default:
      return 'mdi-circle-outline'
  }
}
