import { ref } from 'vue'
import { precurationsAPI, curationsAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { curationStatusLabel } from '@/config/status'
import type { ApiErrorLike } from '@/components/forms/types'

/** Latest precuration per gene (from the scope's precuration list). */
export interface PrecurationStatus {
  id: string
  status: string
  workflow_stage?: string
  updated_at: string
}

/** Latest curation per gene (from the scope's curation list). */
export interface CurationStatus {
  id: string
  status: string
  workflow_stage?: string
  updated_at: string
}

interface WorkflowRecord {
  id: string
  gene_id: string
  status: string
  workflow_stage?: string
  updated_at: string
}

export interface GeneRef {
  gene_id: string
}

/** Keep the approved > submitted > draft ordering; ties go to the newer record. */
export function shouldReplacePrecuration(
  existing: PrecurationStatus,
  newPrecuration: PrecurationStatus
): boolean {
  const statusPriority: Record<string, number> = {
    approved: 3,
    submitted: 2,
    draft: 1,
    rejected: 0
  }
  const existingPriority = statusPriority[existing.status] || 0
  const newPriority = statusPriority[newPrecuration.status] || 0

  if (newPriority > existingPriority) return true
  if (newPriority < existingPriority) return false

  // Same status - use most recent
  return new Date(newPrecuration.updated_at) > new Date(existing.updated_at)
}

/** Keep the active > approved > submitted > draft ordering; ties go to the newer record. */
export function shouldReplaceCuration(
  existing: CurationStatus,
  newCuration: CurationStatus
): boolean {
  const statusPriority: Record<string, number> = {
    active: 5,
    approved: 4,
    submitted: 3,
    draft: 2,
    rejected: 1,
    archived: 0
  }
  const existingPriority = statusPriority[existing.status] || 0
  const newPriority = statusPriority[newCuration.status] || 0

  if (newPriority > existingPriority) return true
  if (newPriority < existingPriority) return false

  // Same status - use most recent
  return new Date(newCuration.updated_at) > new Date(existing.updated_at)
}

const PAGE_SIZE = 200 // Backend max limit is 200

/** Walk every page so large scopes are never silently capped. */
async function fetchAllPages(
  fetchPage: (skip: number) => Promise<{ rows?: WorkflowRecord[]; total?: number }>
): Promise<WorkflowRecord[]> {
  const all: WorkflowRecord[] = []
  for (;;) {
    const { rows = [], total = 0 } = await fetchPage(all.length)
    all.push(...rows)
    if (rows.length === 0 || all.length >= total) return all
  }
}

/**
 * Precuration and curation status per gene for one scope, with the
 * predicates and labels the gene list uses to choose workflow actions.
 */
export function useGeneWorkflowStatus(scopeId: () => string) {
  const logger = useLogger()

  const genePrecurations = ref<Record<string, PrecurationStatus>>({}) // gene_id -> precuration status
  const geneCurations = ref<Record<string, CurationStatus>>({}) // gene_id -> curation status

  /**
   * Fetch precuration statuses for genes in this scope
   * Maps gene_id -> latest precuration status
   */
  async function fetchPrecurationStatuses() {
    try {
      const precurations = await fetchAllPages(async skip => {
        const r = (await precurationsAPI.getPrecurations({
          scope_id: scopeId(),
          skip,
          limit: PAGE_SIZE
        })) as { precurations?: WorkflowRecord[]; total?: number }
        return { rows: r.precurations, total: r.total }
      })

      // Build map of gene_id -> most recent precuration
      const precurationMap: Record<string, PrecurationStatus> = {}
      for (const precuration of precurations) {
        const existing = precurationMap[precuration.gene_id]
        // Keep the most recent or highest-status precuration
        if (!existing || shouldReplacePrecuration(existing, precuration)) {
          precurationMap[precuration.gene_id] = {
            id: precuration.id,
            status: precuration.status,
            workflow_stage: precuration.workflow_stage,
            updated_at: precuration.updated_at
          }
        }
      }
      genePrecurations.value = precurationMap
      logger.debug('Precuration statuses loaded', { count: Object.keys(precurationMap).length })
    } catch (error) {
      logger.error('Failed to fetch precuration statuses', {
        error: (error as ApiErrorLike).message
      })
      // Don't fail the whole page if precurations fail to load
    }
  }

  /**
   * Fetch curation statuses for genes in this scope
   * Maps gene_id -> latest curation status
   */
  async function fetchCurationStatuses() {
    try {
      const curations = await fetchAllPages(async skip => {
        const r = (await curationsAPI.getCurations({
          scope_id: scopeId(),
          skip,
          limit: PAGE_SIZE
        })) as { curations?: WorkflowRecord[]; total?: number }
        return { rows: r.curations, total: r.total }
      })

      // Build map of gene_id -> most recent/highest priority curation
      const curationMap: Record<string, CurationStatus> = {}
      for (const curation of curations) {
        const existing = curationMap[curation.gene_id]
        // Keep the most recent or highest-status curation
        if (!existing || shouldReplaceCuration(existing, curation)) {
          curationMap[curation.gene_id] = {
            id: curation.id,
            status: curation.status,
            workflow_stage: curation.workflow_stage,
            updated_at: curation.updated_at
          }
        }
      }
      geneCurations.value = curationMap
      logger.debug('Curation statuses loaded', { count: Object.keys(curationMap).length })
    } catch (error) {
      logger.error('Failed to fetch curation statuses', { error: (error as ApiErrorLike).message })
      // Don't fail the whole page if curations fail to load
    }
  }

  /** Check if gene has a precuration */
  function hasPrecuration(gene: GeneRef): boolean {
    return !!genePrecurations.value[gene.gene_id]
  }

  /** Check if gene's precuration is approved */
  function isPrecurationApproved(gene: GeneRef): boolean {
    const precuration = genePrecurations.value[gene.gene_id]
    return precuration?.status === 'approved'
  }

  /** Check if gene has a curation */
  function hasCuration(gene: GeneRef): boolean {
    return !!geneCurations.value[gene.gene_id]
  }

  /** Get the curation for a gene */
  function getCuration(gene: GeneRef): CurationStatus | undefined {
    return geneCurations.value[gene.gene_id]
  }

  /** Check if gene's curation is active (completed) */
  function isCurationActive(gene: GeneRef): boolean {
    const curation = geneCurations.value[gene.gene_id]
    return curation?.status === 'active'
  }

  /** Get precuration status label for display */
  function getPrecurationStatusLabel(gene: GeneRef): string {
    const precuration = genePrecurations.value[gene.gene_id]
    if (!precuration) return 'No Precuration'

    const statusLabels: Record<string, string> = {
      draft: 'In Progress',
      submitted: 'Pending Review',
      in_review: 'In Review',
      approved: 'Ready for Curation',
      rejected: 'Needs Revision'
    }
    return statusLabels[precuration.status] || precuration.status
  }

  /** Get curation status label for display */
  function getCurationStatusLabel(gene: GeneRef): string {
    const curation = geneCurations.value[gene.gene_id]
    if (!curation) return 'No Curation'

    return curationStatusLabel(curation.status)
  }

  return {
    genePrecurations,
    geneCurations,
    fetchPrecurationStatuses,
    fetchCurationStatuses,
    hasPrecuration,
    isPrecurationApproved,
    hasCuration,
    getCuration,
    isCurationActive,
    getPrecurationStatusLabel,
    getCurationStatusLabel
  }
}

export type GeneWorkflowStatus = ReturnType<typeof useGeneWorkflowStatus>
