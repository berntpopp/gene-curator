import { computed } from 'vue'
import { getClassification } from '@/config/classification'
import { storedScores } from './curationScores'
export interface ScoredCuration {
  computed_scores?: unknown
  computed_verdict?: string | null
  final_classification?: string | null
  curator_classification_rationale?: string | null
}
const labelOf = (v: string | null | undefined) => (v ? getClassification(v).label : '')
/** `classification` is the calculated verdict, `final` what approval publishes (#533). */
export function useCurationClassification(curation: () => ScoredCuration | null | undefined) {
  const scores = computed(() => storedScores(curation()?.computed_scores))
  const classification = computed(() => labelOf(curation()?.computed_verdict))
  const final = computed(() => labelOf(curation()?.final_classification) || classification.value)
  const rationale = computed(() => curation()?.curator_classification_rationale ?? '')
  return { scores, classification, final, rationale }
}
