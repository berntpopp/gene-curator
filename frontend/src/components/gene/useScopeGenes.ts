import { ref, computed } from 'vue'
import { assignmentsAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { useNotificationsStore } from '@/stores/notifications'
import type { ApiErrorLike, ComponentLogger } from '@/components/forms/types'
import { calculateProgress } from './geneDisplay'
import type { GeneWorkflowStatus } from './useGeneWorkflowStatus'
import type { GeneRow } from './types'

/** Assignment record as returned by the scope assignments endpoint (fields read here). */
interface AssignmentRecord {
  id?: string
  assignment_id?: string
  gene_id: string
  gene_symbol?: string
  gene_name?: string
  gene_hgnc_id?: string
  gene?: { gene_symbol?: string; gene_name?: string; hgnc_id?: string }
  assigned_curator_id?: string | null
  curator_id?: string | null
  curator_name?: string
  curator?: { full_name?: string; email?: string }
  priority?: string
  priority_level?: string
  assignment_notes?: string
  status?: string
  due_date?: string | null
}

/**
 * Assignments of one scope as display rows, with the curator filter options and
 * the search/status/curator filters applied by the gene list.
 */
export function useScopeGenes(scopeId: () => string, workflow: GeneWorkflowStatus) {
  const logger = useLogger() as ComponentLogger
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
          g.gene_name?.toLowerCase().includes(searchLower)
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
      const response = (await assignmentsAPI.getAssignmentsByScope(scopeId())) as AssignmentRecord[]
      genes.value = response.map(assignment => ({
        assignment_id: (assignment.id || assignment.assignment_id) as string,
        gene_id: assignment.gene_id,
        gene_symbol: assignment.gene_symbol || assignment.gene?.gene_symbol || '',
        gene_name: assignment.gene_name || assignment.gene?.gene_name || '',
        gene_hgnc_id: assignment.gene_hgnc_id || assignment.gene?.hgnc_id || '',
        curator_id: assignment.assigned_curator_id || assignment.curator_id,
        curator_name:
          assignment.curator_name ||
          assignment.curator?.full_name ||
          assignment.curator?.email ||
          '',
        priority: assignment.priority || assignment.priority_level || 'normal',
        assignment_notes: assignment.assignment_notes || '',
        status: assignment.status || 'assigned',
        due_date: assignment.due_date,
        progress: calculateProgress(assignment)
      }))

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
