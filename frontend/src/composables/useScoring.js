/**
 * Composable for ClinGen SOP v11 scoring calculations
 *
 * Provides client-side scoring breakdown for UI display
 * (Final scores are calculated by backend for accuracy)
 *
 * @example
 * import { useScoring } from '@/composables/useScoring'
 *
 * const { breakdown, classificationColor } = useScoring(evidenceItems)
 */

import { computed } from 'vue'

export function useScoring(evidenceItems) {
  /**
   * Calculate scoring breakdown from evidence items
   */
  const breakdown = computed(() => {
    const genetic = evidenceItems.value.filter(e => e.evidence_type === 'genetic')
    const experimental = evidenceItems.value.filter(e => e.evidence_type === 'experimental')

    // Genetic scores by category
    const case_level_score = genetic
      .filter(e => e.evidence_category === 'case_level')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const segregation_score = genetic
      .filter(e => e.evidence_category === 'segregation')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const case_control_score = genetic
      .filter(e => e.evidence_category === 'case_control')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const genetic_total = Math.min(case_level_score + segregation_score + case_control_score, 12.0)

    // Experimental scores by category
    const expression_score = experimental
      .filter(e => e.evidence_category === 'expression')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const function_score = experimental
      .filter(e => e.evidence_category === 'protein_function')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const models_score = experimental
      .filter(e => e.evidence_category === 'models')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const rescue_score = experimental
      .filter(e => e.evidence_category === 'rescue')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const experimental_total = Math.min(
      expression_score + function_score + models_score + rescue_score,
      6.0
    )

    const total_score = genetic_total + experimental_total

    // Classification based on ClinGen SOP v11
    let classification = 'No Known Disease Relationship'
    if (total_score >= 12) classification = 'Definitive'
    else if (total_score >= 7) classification = 'Strong'
    else if (total_score >= 2) classification = 'Moderate'
    else if (total_score >= 0.1) classification = 'Limited'

    return {
      genetic_total,
      experimental_total,
      total_score,
      classification,
      case_level_score: Math.min(case_level_score, 12),
      segregation_score: Math.min(segregation_score, 7),
      case_control_score: Math.min(case_control_score, 6),
      expression_score: Math.min(expression_score, 2),
      function_score: Math.min(function_score, 2),
      models_score: Math.min(models_score, 4),
      rescue_score: Math.min(rescue_score, 2)
    }
  })

  /**
   * Get Vuetify color for classification
   */
  const classificationColor = computed(() => {
    const cls = breakdown.value.classification
    if (cls === 'Definitive') return 'success'
    if (cls === 'Strong') return 'info'
    if (cls === 'Moderate') return 'warning'
    if (cls === 'Limited') return 'grey'
    return 'error'
  })

  /**
   * Get progress percentage (0-100)
   */
  const progressPercentage = computed(() => {
    const total = breakdown.value.total_score
    return Math.min((total / 12) * 100, 100)
  })

  /**
   * Check if score is sufficient for classification
   */
  const isSufficientEvidence = computed(() => {
    return breakdown.value.total_score >= 0.1
  })

  return {
    breakdown,
    classificationColor,
    progressPercentage,
    isSufficientEvidence
  }
}
