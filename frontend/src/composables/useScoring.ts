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
import type { ComputedRef } from 'vue'

/** Minimal evidence shape used for scoring (backend EvidenceItem fields). */
export interface ScoredEvidence {
  evidence_type?: string | null
  evidence_category?: string | null
  computed_score?: number | null
}

export interface ScoringBreakdown {
  genetic_total: number
  experimental_total: number
  total_score: number
  classification: string
  case_level_score: number
  segregation_score: number
  case_control_score: number
  expression_score: number
  function_score: number
  models_score: number
  rescue_score: number
}

export interface UseScoringReturn {
  breakdown: ComputedRef<ScoringBreakdown>
  classificationColor: ComputedRef<string>
  progressPercentage: ComputedRef<number>
  isSufficientEvidence: ComputedRef<boolean>
}

const sumScores = (items: readonly ScoredEvidence[], category: string): number =>
  items
    .filter(e => e.evidence_category === category)
    .reduce((sum, e) => sum + (e.computed_score || 0), 0)

export function useScoring(evidenceItems: {
  readonly value: readonly ScoredEvidence[]
}): UseScoringReturn {
  /**
   * Calculate scoring breakdown from evidence items
   */
  const breakdown = computed<ScoringBreakdown>(() => {
    const genetic = evidenceItems.value.filter(e => e.evidence_type === 'genetic')
    const experimental = evidenceItems.value.filter(e => e.evidence_type === 'experimental')

    // Genetic scores by category
    const case_level_score = sumScores(genetic, 'case_level')
    const segregation_score = sumScores(genetic, 'segregation')
    const case_control_score = sumScores(genetic, 'case_control')

    const genetic_total = Math.min(case_level_score + segregation_score + case_control_score, 12.0)

    // Experimental scores by category
    const expression_score = sumScores(experimental, 'expression')
    const function_score = sumScores(experimental, 'protein_function')
    const models_score = sumScores(experimental, 'models')
    const rescue_score = sumScores(experimental, 'rescue')

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
  const classificationColor = computed<string>(() => {
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
  const progressPercentage = computed<number>(() => {
    const total = breakdown.value.total_score
    return Math.min((total / 12) * 100, 100)
  })

  /**
   * Check if score is sufficient for classification
   */
  const isSufficientEvidence = computed<boolean>(() => {
    return breakdown.value.total_score >= 0.1
  })

  return {
    breakdown,
    classificationColor,
    progressPercentage,
    isSufficientEvidence
  }
}
