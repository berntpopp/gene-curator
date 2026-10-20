import { ref, computed } from 'vue'
import { assignmentsAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { useNotificationsStore } from '@/stores/notifications'
import type { ApiErrorLike } from '@/components/forms/types'
import { calculateProgress } from './geneDisplay'
import type { GeneWorkflowStatus } from './useGeneWorkflowStatus'
import type { GeneRow } from './types'

/**
 * Assignments of one scope as display rows, with the curator filter options and
 * the search/status/curator filters applied by the gene list.
 */
export function useScopeGenes(scopeId: () => string, workflow: GeneWorkflowStatus) {
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // State
  const genes = ref<GeneRow[]>([])
  const loading = ref(false)
  const search = ref('')
  const filterStatus = ref<string | null>(null)
  const filterCurator = ref<string | null>(null)
  const curators = ref<Array<{ user_id: string; user_name: string; user_email?: string }>>([])

  // Curator options (for filter)
  const curatorOptions = computed(() => {
    return curators.value.map(c => ({
      id: c.user_id,
      name: c.user_name || c.user_email
    }))
  })

  // Filtered genes
  const filteredGenes = computed(() => {
    let result = genes.value

    // Search filter
    if (search.value) {
      const searchLower = search.value.toLowerCase()
      result = result.filter(
        g =>
          g.gene_symbol?.toLowerCase().includes(searchLower) ||
          g.gene_hgnc_id.toLowerCase().includes(searchLower)
      )
    }

    // Status filter
    if (filterStatus.value) {
      result = result.filter(g => g.status === filterStatus.value)
    }

    // Curator filter
    if (filterCurator.value) {
      result = result.filter(g => g.curator_id === filterCurator.value)
    }

    return result
  })

  /**
   * Fetch genes assigned to scope
   */
  async function fetchGenes() {
    loading.value = true
    try {
      const response = await assignmentsAPI.getAssignmentsByScope(scopeId())
      genes.value = response.map(assignment => {
        // The API carries no assignment status; derive it from active curation work
        const status = assignment.has_active_work ? 'in_progress' : 'assigned'
        return {
          assignment_id: assignment.id,
          gene_id: assignment.gene_id,
          gene_symbol: assignment.gene_symbol,
          gene_hgnc_id: assignment.gene_hgnc_id,
          curator_id: assignment.assigned_curator_id,
          curator_name: assignment.curator_name ?? '',
          priority: assignment.priority,
          assignment_notes: '',
          status,
          progress: calculateProgress({ status })
        }
      })

      // Extract unique curators for filter
      curators.value = Array.from(
        new Map(
          genes.value
            .filter(g => g.curator_id)
            .map(g => [
              g.curator_id,
              { user_id: g.curator_id as string, user_name: g.curator_name }
            ])
        ).values()
      )

      // Fetch precuration and curation status for all genes in scope
      await Promise.all([workflow.fetchPrecurationStatuses(), workflow.fetchCurationStatuses()])

      logger.debug('Genes loaded', { count: genes.value.length, scope_id: scopeId() })
    } catch (error) {
      logger.error('Failed to fetch genes', { error: (error as ApiErrorLike).message })
      notificationStore.addToast('Failed to load genes', 'error')
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear all filters
   */
  function clearFilters() {
    search.value = ''
    filterStatus.value = null
    filterCurator.value = null
  }

  return {
    genes,
    loading,
    search,
    filterStatus,
    filterCurator,
    curatorOptions,
    filteredGenes,
    fetchGenes,
    clearFilters
  }
}
