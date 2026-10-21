import { computed } from 'vue'
import { hasContent } from '@/components/clingen/hasContent'
import { classifyScores, computeScores, type EvidenceData } from './curationScores'

/** Evidence scores and the ClinGen classification derived from a curation's evidence_data. */
export function useCurationClassification(evidence: () => EvidenceData | null | undefined) {
  const scores = computed(() => computeScores(evidence()))
  const classification = computed(() => {
    const data = evidence() as
      { contradictory_evidence?: unknown[]; replicated_over_time?: boolean } | null | undefined
    return classifyScores(
      scores.value.total,
      scores.value.genetic,
      hasContent(data?.contradictory_evidence),
      data?.replicated_over_time === true
    )
  })
  return { scores, classification }
}
