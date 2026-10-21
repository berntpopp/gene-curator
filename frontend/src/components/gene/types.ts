/**
 * Shared types for the gene components.
 */
import type { GeneStage } from './geneStage'

/** One row of the scope gene list (an assignment flattened for display). */
export type GeneRow = {
  assignment_id: string
  gene_id: string
  gene_symbol: string
  gene_hgnc_id: string
  curator_id?: string | null
  curator_name: string
  priority: string
  assignment_notes: string
  due_date?: string | null
  stage: GeneStage
  /** Latest activity: the newest precuration/curation update, else the assignment date. */
  updated_at: string
  curation_id?: string
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
