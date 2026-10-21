import { computed } from 'vue'
import { getClassification } from '@/config/classification'
import { storedScores, type StoredScores } from './curationScores'

export interface ScoredCuration {
  computed_scores?: StoredScores | null
  computed_verdict?: string | null
}

/** Stored scores and the stored classification of a curation (no client recalculation). */
export function useCurationClassification(curation: () => ScoredCuration | null | undefined) {
  const scores = computed(() => storedScores(curation()?.computed_scores))
  // Label form ("Moderate"), as the approve checklist and ClassificationMark expect
  const classification = computed(() => {
    const verdict = curation()?.computed_verdict
    return verdict ? getClassification(verdict).label : ''
  })
  return { scores, classification }
}
