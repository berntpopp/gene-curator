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
import { useEvidenceStore } from '@/stores/evidence.js'

export function useEvidence(curationId) {
  const evidenceStore = useEvidenceStore()

  const loading = ref(false)
  const error = ref(null)

  // Computed properties
  const evidenceItems = computed(() => {
    return evidenceStore.getEvidenceByCuration(curationId)
  })

  const geneticEvidence = computed(() => {
    return evidenceItems.value.filter(item => item.evidence_type === 'genetic')
  })

  const experimentalEvidence = computed(() => {
    return evidenceItems.value.filter(item => item.evidence_type === 'experimental')
  })

  const totalScore = computed(() => {
    return evidenceItems.value.reduce((sum, item) => {
      return sum + (item.computed_score || 0)
    }, 0)
  })

  const evidenceByCategory = computed(() => {
    const categories = {}
    evidenceItems.value.forEach(item => {
      if (!categories[item.evidence_category]) {
        categories[item.evidence_category] = []
      }
      categories[item.evidence_category].push(item)
    })
    return categories
  })

  // Actions
  async function fetchEvidence() {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.fetchEvidenceForCuration(curationId)
    } catch (e) {
      error.value = e.message || 'Failed to fetch evidence'
    } finally {
      loading.value = false
    }
  }

  async function addEvidence(data) {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.createEvidence(curationId, data)
    } catch (e) {
      error.value = e.message || 'Failed to add evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateEvidence(itemId, data) {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.updateEvidence(curationId, itemId, data)
    } catch (e) {
      error.value = e.message || 'Failed to update evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function removeEvidence(itemId) {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.deleteEvidence(curationId, itemId)
    } catch (e) {
      error.value = e.message || 'Failed to delete evidence'
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
