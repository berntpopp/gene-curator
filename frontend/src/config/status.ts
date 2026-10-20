/**
 * Curation status labels and colours. One place for every view that shows a curation status.
 * Typed from the generated API enum, so a value the backend does not send fails vue-tsc.
 */
import type { Schema } from '@/types/api'

export type CurationStatus = Schema<'CurationStatus'>

export const CURATION_STATUS: Record<CurationStatus, { label: string; color: string }> = {
  draft: { label: 'Draft', color: 'grey' },
  submitted: { label: 'Submitted', color: 'info' },
  in_review: { label: 'In review', color: 'warning' },
  approved: { label: 'Approved', color: 'success' },
  rejected: { label: 'Rejected', color: 'error' },
  active: { label: 'Active', color: 'primary' },
  archived: { label: 'Archived', color: 'grey' }
}

/** Label for a status value; unknown values fall back to the raw string. */
export function curationStatusLabel(status: string | null | undefined): string {
  if (!status) return 'Unknown'
  return CURATION_STATUS[status as CurationStatus]?.label ?? status
}

/** Chip colour for a status value; unknown values are grey. */
export function curationStatusColor(status: string | null | undefined): string {
  return CURATION_STATUS[status as CurationStatus]?.color ?? 'grey'
}
