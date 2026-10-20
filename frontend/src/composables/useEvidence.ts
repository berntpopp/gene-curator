/**
 * Composable for evidence management
 *
 * Provides convenient access to evidence store actions and computed values
 *
 * @example
 * import { useEvidence } from '@/composables/useEvidence'
 *
 * const {
 *   evidenceItems,
 *   geneticEvidence,
 *   totalScore,
 *   fetchEvidence,
 *   addEvidence,
 *   updateEvidence,
 *   removeEvidence
 * } = useEvidence(curationId)
 */

import { computed, ref } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { useEvidenceStore } from '@/stores/evidence'
import type { ScoredEvidence } from './useScoring'

/** Evidence item as used by this composable (fields beyond these are passed through). */
export interface EvidenceItem extends ScoredEvidence {
  [key: string]: unknown
}

export interface UseEvidenceReturn {
  loading: Ref<boolean>
  error: Ref<string | null>
  evidenceItems: ComputedRef<EvidenceItem[]>
  geneticEvidence: ComputedRef<EvidenceItem[]>
  experimentalEvidence: ComputedRef<EvidenceItem[]>
  totalScore: ComputedRef<number>
  evidenceByCategory: ComputedRef<Record<string, EvidenceItem[]>>
  fetchEvidence: () => Promise<void>
  addEvidence: (data: Record<string, unknown>) => Promise<void>
  updateEvidence: (itemId: string, data: Record<string, unknown>) => Promise<void>
  removeEvidence: (itemId: string) => Promise<void>
}

export function useEvidence(curationId: string): UseEvidenceReturn {
  const evidenceStore = useEvidenceStore()

  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed properties
  const evidenceItems = computed<EvidenceItem[]>(() => {
    return evidenceStore.getEvidenceByCuration(curationId)
  })

  const geneticEvidence = computed<EvidenceItem[]>(() => {
    return evidenceItems.value.filter(item => item.evidence_type === 'genetic')
  })

  const experimentalEvidence = computed<EvidenceItem[]>(() => {
    return evidenceItems.value.filter(item => item.evidence_type === 'experimental')
  })

  const totalScore = computed<number>(() => {
    return evidenceItems.value.reduce((sum, item) => {
      return sum + (item.computed_score || 0)
    }, 0)
  })

  const evidenceByCategory = computed<Record<string, EvidenceItem[]>>(() => {
    const categories: Record<string, EvidenceItem[]> = {}
    evidenceItems.value.forEach(item => {
      const category = String(item.evidence_category)
      if (!categories[category]) {
        categories[category] = []
      }
      categories[category].push(item)
    })
    return categories
  })

  // Actions
  async function fetchEvidence(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.fetchEvidenceForCuration(curationId)
    } catch (e) {
      error.value = (e instanceof Error && e.message) || 'Failed to fetch evidence'
    } finally {
      loading.value = false
    }
  }

  async function addEvidence(data: Record<string, unknown>): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.createEvidence(curationId, data)
    } catch (e) {
      error.value = (e instanceof Error && e.message) || 'Failed to add evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateEvidence(itemId: string, data: Record<string, unknown>): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.updateEvidence(curationId, itemId, data)
    } catch (e) {
      error.value = (e instanceof Error && e.message) || 'Failed to update evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function removeEvidence(itemId: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.deleteEvidence(curationId, itemId)
    } catch (e) {
      error.value = (e instanceof Error && e.message) || 'Failed to delete evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    loading,
    error,

    // Computed
    evidenceItems,
    geneticEvidence,
    experimentalEvidence,
    totalScore,
    evidenceByCategory,

    // Actions
    fetchEvidence,
    addEvidence,
    updateEvidence,
    removeEvidence
  }
}
