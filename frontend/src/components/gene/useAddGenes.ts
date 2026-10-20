import type { Ref } from 'vue'
import { genesAPI, assignmentsAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { useNotificationsStore } from '@/stores/notifications'
import type { ApiErrorLike, ComponentLogger } from '@/components/forms/types'
import type { Schema } from '@/types/api'

export type HgncGene = Schema<'HGNCGeneSearchResult'>

/** One row of the bulk validation table. */
export interface BulkValidationResult {
  status: string
  gene?: HgncGene | null
  alternatives?: HgncGene[]
  message?: string | null
  [key: string]: unknown
}

interface BulkCreateResponse {
  total_created: number
  total_skipped: number
  total_errors: number
  created_genes?: Array<{ id: string }>
}

export interface AddGenesOptions {
  scopeId: () => string | null
  selectedGene: Ref<HgncGene | null>
  bulkValidationResults: Ref<BulkValidationResult[]>
  skipDuplicates: Ref<boolean>
}

/**
 * Create catalogue genes (single or bulk from validated HGNC results) and
 * optionally assign them to the current scope.
 */
export function useAddGenes(options: AddGenesOptions) {
  const logger = useLogger() as ComponentLogger
  const notificationStore = useNotificationsStore()
  const { scopeId, selectedGene, bulkValidationResults, skipDuplicates } = options

  /**
   * Add single gene
   */
  async function addSingleGene() {
    const gene = selectedGene.value
    if (!gene) return
    const geneData = {
      hgnc_id: gene.hgnc_id,
      approved_symbol: gene.symbol,
      chromosome: gene.chromosome || undefined,
      location: gene.location || undefined,
      previous_symbols: gene.previous_symbols || undefined,
      alias_symbols: gene.alias_symbols || undefined,
      details: gene.name ? { approved_name: gene.name } : undefined
    }

    logger.debug('Adding single gene', { gene_data: geneData })

    const result = (await genesAPI.createGene(geneData)) as {
      id: string
      hgnc_id: string
      approved_symbol: string
    }

    logger.info('Gene added successfully', {
      gene_id: result.id,
      hgnc_id: result.hgnc_id,
      symbol: result.approved_symbol
    })

    // If scopeId is provided, also assign the gene to the scope (unassigned status)
    if (scopeId()) {
      try {
        await assignmentsAPI.createAssignment({
          gene_id: result.id,
          scope_id: scopeId(),
          assigned_curator_id: null, // Unassigned
          priority_level: 'medium'
        })
        logger.info('Gene assigned to scope', {
          gene_id: result.id,
          scope_id: scopeId()
        })
        notificationStore.addToast(
          `Gene ${result.approved_symbol} added and assigned to scope`,
          'success'
        )
      } catch (assignError) {
        // Gene was added but assignment failed - still report success for gene creation
        logger.warn('Gene added but scope assignment failed', {
          gene_id: result.id,
          scope_id: scopeId(),
          error: (assignError as ApiErrorLike).message
        })
        notificationStore.addToast(
          `Gene ${result.approved_symbol} added (assignment failed: ${((assignError as ApiErrorLike).response as { data?: { detail?: string } } | undefined)?.data?.detail || (assignError as ApiErrorLike).message})`,
          'warning'
        )
      }
    } else {
      notificationStore.addToast(`Gene ${result.approved_symbol} added successfully`, 'success')
    }
  }

  /**
   * Add bulk genes
   */
  async function addBulkGenes() {
    // Get valid genes (valid status or accepted suggestions)
    const genesToAdd = bulkValidationResults.value
      .filter(
        (r): r is BulkValidationResult & { gene: HgncGene } => r.status === 'valid' && !!r.gene
      )
      .map(r => ({
        hgnc_id: r.gene.hgnc_id,
        approved_symbol: r.gene.symbol,
        chromosome: r.gene.chromosome || undefined,
        location: r.gene.location || undefined,
        details: r.gene.name ? { approved_name: r.gene.name } : undefined
      }))

    if (genesToAdd.length === 0) {
      notificationStore.addToast('No valid genes to add', 'warning')
      return
    }

    logger.debug('Adding bulk genes', {
      count: genesToAdd.length,
      skip_duplicates: skipDuplicates.value
    })

    const result = (await genesAPI.bulkCreateGenes({
      genes: genesToAdd,
      skip_duplicates: skipDuplicates.value
    })) as BulkCreateResponse

    logger.info('Bulk genes added', {
      created: result.total_created,
      skipped: result.total_skipped,
      failed: result.total_errors
    })

    // If scopeId is provided and genes were created, assign them to the scope
    if (scopeId() && result.created_genes && result.created_genes.length > 0) {
      try {
        const geneIds = (result.created_genes ?? []).map(g => g.id)
        await assignmentsAPI.bulkAssignGenes({
          gene_ids: geneIds,
          scope_id: scopeId(),
          assigned_curator_id: null // Unassigned
        })
        logger.info('Bulk genes assigned to scope', {
          gene_count: geneIds.length,
          scope_id: scopeId()
        })
        notificationStore.addToast(
          `Added and assigned ${result.total_created} genes (${result.total_skipped} skipped, ${result.total_errors} failed)`,
          result.total_errors > 0 ? 'warning' : 'success'
        )
      } catch (assignError) {
        logger.warn('Genes added but scope assignment failed', {
          gene_count: result.created_genes?.length ?? 0,
          scope_id: scopeId(),
          error: (assignError as ApiErrorLike).message
        })
        notificationStore.addToast(
          `Added ${result.total_created} genes but scope assignment failed: ${((assignError as ApiErrorLike).response as { data?: { detail?: string } } | undefined)?.data?.detail || (assignError as ApiErrorLike).message}`,
          'warning'
        )
      }
    } else {
      notificationStore.addToast(
        `Added ${result.total_created} genes (${result.total_skipped} skipped, ${result.total_errors} failed)`,
        result.total_errors > 0 ? 'warning' : 'success'
      )
    }
  }

  return { addSingleGene, addBulkGenes }
}
