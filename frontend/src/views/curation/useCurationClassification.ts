import { computed } from 'vue'
import { getClassification } from '@/config/classification'
import { storedScores } from './curationScores'
export interface ScoredCuration {
  computed_scores?: unknown
  computed_verdict?: string | null
}
export function useCurationClassification(curation: () => ScoredCuration | null | undefined) {
  const scores = computed(() => storedScores(curation()?.computed_scores))
  const classification = computed(() => {
    const verdict = curation()?.computed_verdict
    return verdict ? getClassification(verdict).label : ''
  })
  return { scores, classification }
}
