import { ref, computed } from 'vue'
import { assignmentsAPI } from '@/api'
import { useLogger } from '@/composables/useLogger'
import { useNotificationsStore } from '@/stores/notifications'
import type { useTableUrlState } from '@/composables/useTableUrlState'
import type { ApiErrorLike } from '@/components/forms/types'
import { GENE_STAGES, stageOf, type GeneStage } from './geneStage'
import type { GeneWorkflowStatus } from './useGeneWorkflowStatus'
import type { GeneRow } from './types'

type TableState = ReturnType<typeof useTableUrlState>
type Assignment = Awaited<ReturnType<typeof assignmentsAPI.getAssignmentsByScope>>[number]

const PRIORITY_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 }
const STAGE_RANK = Object.fromEntries(GENE_STAGES.map((s, i) => [s.value, i]))

/**
 * Assignments of one scope as display rows. Search, filters (stage, curator, priority), sort and
 * paging come from the URL-backed table state, applied here on the client.
 */
export function useScopeGenes(scopeId: () => string, workflow: GeneWorkflowStatus, t: TableState) {
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  const assignments = ref<Assignment[]>([])
  const loading = ref(false)

  const rows = computed<GeneRow[]>(() =>
    assignments.value.map(a => {
      const pre = workflow.genePrecurations.value[a.gene_id]
      const cur = workflow.geneCurations.value[a.gene_id]
      const updated = [a.assigned_at, pre?.updated_at, cur?.updated_at].filter(Boolean) as string[]
      return {
        assignment_id: a.id,
        gene_id: a.gene_id,
        gene_symbol: a.gene_symbol,
        gene_hgnc_id: a.gene_hgnc_id,
        curator_id: a.assigned_curator_id,
        curator_name: a.curator_name ?? '',
        priority: a.priority,
        due_date: a.due_date,
        assignment_notes: '',
        stage: stageOf(!!a.assigned_curator_id, pre, cur),
        updated_at: updated.sort().at(-1) ?? '',
        curation_id: cur?.id
      }
    })
  )

  const stageCounts = computed(() => {
    const counts = Object.fromEntries(GENE_STAGES.map(s => [s.value, 0])) as Record<
      GeneStage,
      number
    >
    for (const r of rows.value) counts[r.stage]++
    return counts
  })

  const curatorOptions = computed(() =>
    [
      ...new Map(
        rows.value.filter(r => r.curator_id).map(r => [r.curator_id!, r.curator_name])
      ).entries()
    ].map(([value, title]) => ({ value, title }))
  )

  const filteredGenes = computed(() => {
    const q = t.search.value.trim().toLowerCase()
    const f = t.filters.value
    const sort = t.sortBy.value[0]
    const key = (r: GeneRow): string | number =>
      sort?.key === 'stage'
        ? STAGE_RANK[r.stage]!
        : sort?.key === 'priority'
          ? (PRIORITY_RANK[r.priority] ?? 3)
          : String(r[(sort?.key ?? 'gene_symbol') as keyof GeneRow] ?? '').toLowerCase()
    const sign = sort?.order === 'desc' ? -1 : 1
    return rows.value
      .filter(
        r =>
          (!q ||
            [r.gene_symbol, r.gene_hgnc_id, r.curator_name].some(v =>
              v?.toLowerCase().includes(q)
            )) &&
          (!f.stage || r.stage === f.stage) &&
          (!f.curator || r.curator_id === f.curator) &&
          (!f.priority || r.priority === f.priority)
      )
      .sort((a, b) => (key(a) < key(b) ? -sign : key(a) > key(b) ? sign : 0))
  })

  const pageRows = computed(() => {
    const size = t.itemsPerPage.value
    return filteredGenes.value.slice((t.page.value - 1) * size, t.page.value * size)
  })

  /** Fetch the scope's assignments and the precuration/curation status of its genes. */
  async function fetchGenes() {
    loading.value = true
    try {
      // ponytail: one request of up to 1000 rows (the backend maximum); page through above that
      assignments.value = await assignmentsAPI.getAssignmentsByScope(scopeId(), { limit: 1000 })
      await Promise.all([workflow.fetchPrecurationStatuses(), workflow.fetchCurationStatuses()])
      logger.debug('Genes loaded', { count: assignments.value.length, scope_id: scopeId() })
    } catch (error) {
      logger.error('Failed to fetch genes', { error: (error as ApiErrorLike).message })
      notificationStore.addToast('Failed to load genes', 'error')
    } finally {
      loading.value = false
    }
  }

  return { loading, rows, stageCounts, curatorOptions, filteredGenes, pageRows, fetchGenes }
}
