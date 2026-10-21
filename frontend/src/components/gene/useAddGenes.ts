import type { Ref } from 'vue'
import { genesAPI, assignmentsAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { useNotificationsStore } from '@/stores/notifications'
import type { ApiErrorLike } from '@/components/forms/types'
import type { Schema } from '@/types/api'
import type { BulkValidationEntry } from '@/composables/useHgncSearch'

export type HgncGene = Schema<'HGNCGeneSearchResult'>

/** One row of the bulk validation table. */
export type BulkValidationResult = BulkValidationEntry

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
const errorDetail = (e: unknown): string =>
  ((e as ApiErrorLike).response as { data?: { detail?: string } } | undefined)?.data?.detail ||
  (e as ApiErrorLike).message ||
  ''

export function useAddGenes(options: AddGenesOptions) {
  const logger = useLogger()
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

    // The catalogue is shared: reuse the gene when its HGNC ID already exists (#189)
    const existing = (await genesAPI.searchGenes({ hgnc_id: gene.hgnc_id }))[0]
    const result = existing ?? (await genesAPI.createGene(geneData))

    logger.info(existing ? 'Gene already in catalogue' : 'Gene added successfully', {
      gene_id: result.id,
      hgnc_id: result.hgnc_id,
      symbol: result.approved_symbol
    })

    // If scopeId is provided, also assign the gene to the scope (unassigned status)
    const targetScopeId = scopeId()
    if (targetScopeId) {
      try {
        await assignmentsAPI.createAssignment({
          gene_id: result.id,
          scope_id: targetScopeId,
          assigned_curator_id: null, // Unassigned
          priority_level: 'medium'
        })
        logger.info('Gene assigned to scope', {
          gene_id: result.id,
          scope_id: targetScopeId
        })
        notificationStore.addToast(
          `Gene ${result.approved_symbol} added and assigned to scope`,
          'success'
        )
      } catch (assignError) {
        const detail = errorDetail(assignError)
        if (detail.includes('already assigned')) {
          notificationStore.addToast(
            `Gene ${result.approved_symbol} is already in this scope`,
            'info'
          )
          return
        }
        // Gene was added but assignment failed - still report success for gene creation
        logger.warn('Gene added but scope assignment failed', {
          gene_id: result.id,
          scope_id: targetScopeId,
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

    const result = await genesAPI.bulkCreateGenes({
      genes: genesToAdd,
      validate_hgnc: true,
      skip_duplicates: skipDuplicates.value
    })

    logger.info('Bulk genes added', {
      created: result.total_created,
      skipped: result.total_skipped,
      failed: result.total_errors
    })

    // If scopeId is provided and genes were created, assign them to the scope
    const targetScopeId = scopeId()
    if (targetScopeId) {
      try {
        // Genes skipped as duplicates are already in the catalogue: assign them too
        const found = await Promise.all(
          result.skipped_genes.map(
            async s => (await genesAPI.searchGenes({ hgnc_id: s.hgnc_id }))[0]
          )
        )
        const geneIds = [...result.created_genes, ...found.filter(g => !!g)].map(g => g.id)
        const assigned = geneIds.length
          ? await assignmentsAPI.bulkAssignGenes({
              gene_ids: geneIds,
              scope_id: targetScopeId,
              assigned_curator_id: null, // Unassigned
              priority_level: 'medium'
            })
          : null
        logger.info('Bulk genes assigned to scope', {
          gene_count: geneIds.length,
          scope_id: targetScopeId
        })
        const failed = result.total_errors + (assigned?.total_errors ?? 0)
        notificationStore.addToast(
          `Added ${assigned?.total_created ?? 0} genes to the scope (${assigned?.total_skipped ?? 0} already in scope, ${failed} failed)`,
          failed > 0 ? 'warning' : 'success'
        )
      } catch (assignError) {
        logger.warn('Genes added but scope assignment failed', {
          gene_count: result.created_genes.length,
          scope_id: targetScopeId,
          error: (assignError as ApiErrorLike).message
        })
        notificationStore.addToast(
          `Added ${result.total_created} genes but scope assignment failed: ${errorDetail(assignError)}`,
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
