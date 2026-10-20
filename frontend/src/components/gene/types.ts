/**
 * Shared types for the gene components.
 */
import type { ComponentLogger } from '@/components/forms/types'

export type { ComponentLogger }

/** One row of the scope gene list (an assignment flattened for display). */
export interface GeneRow {
  assignment_id: string
  gene_id: string
  gene_symbol: string
  gene_name: string
  gene_hgnc_id: string
  curator_id?: string | null
  curator_name: string
  priority: string
  assignment_notes: string
  status: string
  due_date?: string | null
  progress: number
}

/** Scope member mapped to a curator choice (see fetchAvailableCurators in the assign/reassign modals). */
export interface CuratorOption {
  user_id: string
  role: string
  full_name?: string | null
  email?: string | null
  displayName: string
  [key: string]: unknown
}
