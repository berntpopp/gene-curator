/**
 * Schema-agnostic scoring composable
 * Works with ClinGen, GenCC, Qualitative engines
 *
 * Provides reactive computed properties for score display based on
 * validation results from backend scoring engines.
 *
 * @example
 * import { useSchemaScoring } from '@/composables/useSchemaScoring'
 *
 * const {
 *   totalScore,
 *   categoryScores,
 *   classification,
 *   classificationColor,
 *   nearThreshold
 * } = useSchemaScoring(scoreCalculations, scoringConfiguration)
 */

import { computed } from 'vue'
import type { ComputedRef } from 'vue'

/** Subset of a backend scoring engine configuration used for display. */
export interface ScoringConfiguration {
  classification_thresholds?: Record<string, number>
  max_score?: number
  max_scores?: Record<string, number>
  scoring_rules?: Record<string, { max_score?: number }>
}

export interface UseSchemaScoringReturn {
  totalScore: ComputedRef<number>
  categoryScores: ComputedRef<Record<string, unknown>>
  classification: ComputedRef<string | null>
  classificationColor: ComputedRef<string>
  nearThreshold: ComputedRef<boolean>
  maxScore: ComputedRef<number>
  progressPercentage: ComputedRef<number>
}

export function useSchemaScoring(
  scoreCalculations: { readonly value: Record<string, unknown> | null | undefined },
  scoringConfiguration: { readonly value: ScoringConfiguration | null | undefined }
): UseSchemaScoringReturn {
  /**
   * The backend's `total_score` is the source of truth (#157); until every engine
   * returns it, sum the category entries and skip section totals (`*_total`).
   */
  const totalScore = computed<number>(() => {
    const calc = scoreCalculations.value
    if (!calc) return 0
    if (typeof calc.total_score === 'number') return calc.total_score

    return Object.entries(calc).reduce<number>(
      (sum, [key, value]) =>
        typeof value === 'number' && !key.endsWith('_total') ? sum + value : sum,
      0
    )
  })

  /**
   * Extract category scores (all score_calculations entries)
   */
  const categoryScores = computed<Record<string, unknown>>(() => {
    if (!scoreCalculations.value) return {}
    return { ...scoreCalculations.value }
  })

  /**
   * Get classification thresholds from scoring configuration
   */
  const thresholds = computed<Record<string, number>>(() => {
    return scoringConfiguration.value?.classification_thresholds || {}
  })

  /**
   * Determine classification based on total score and thresholds
   * Returns the highest classification level that the score meets
   */
  const classification = computed<string | null>(() => {
    const score = totalScore.value
    const thresh = thresholds.value

    if (!thresh || Object.keys(thresh).length === 0) {
      return null
    }

    // Sort thresholds by value (descending) to check highest first
    const sortedLevels = Object.entries(thresh).sort(([, a], [, b]) => b - a)

    // Find first threshold that score meets or exceeds
    for (const [level, requiredScore] of sortedLevels) {
      if (score >= requiredScore) {
        return level
      }
    }

    // If no threshold met, return lowest classification or null
    return sortedLevels.length > 0 ? (sortedLevels[sortedLevels.length - 1]?.[0] ?? null) : null
  })

  /**
   * Get Vuetify color for classification
   * Maps common classification levels to semantic colors
   */
  const classificationColor = computed<string>(() => {
    const cls = classification.value
    if (!cls) return 'grey'

    const clsLower = cls.toLowerCase()

    // Strong evidence classifications
    if (clsLower.includes('definitive') || clsLower.includes('strong')) {
      return 'success'
    }

    // Moderate evidence
    if (clsLower.includes('moderate')) {
      return 'info'
    }

    // Limited evidence
    if (clsLower.includes('limited') || clsLower.includes('disputed')) {
      return 'warning'
    }

    // No evidence / refuted
    if (clsLower.includes('none') || clsLower.includes('refuted') || clsLower.includes('no')) {
      return 'grey'
    }

    return 'grey'
  })

  /**
   * Check if score is within 1 point of next classification threshold
   */
  const nearThreshold = computed<boolean>(() => {
    const score = totalScore.value
    const thresh = thresholds.value

    if (!thresh || Object.keys(thresh).length === 0) {
      return false
    }

    // Sort thresholds ascending to find next level
    const sortedThresholds = Object.entries(thresh)
      .sort(([, a], [, b]) => a - b)
      .map(([, value]) => value)

    // Find next threshold above current score
    const nextThreshold = sortedThresholds.find(t => t > score)

    if (!nextThreshold) return false

    // Check if within 1 point
    return nextThreshold - score <= 1
  })

  /**
   * Get maximum possible score from scoring configuration
   * Falls back to dynamic calculation from max_scores if available
   */
  const maxScore = computed<number>(() => {
    const config = scoringConfiguration.value

    if (!config) return 0

    // Check for explicit max_score
    if (config.max_score !== undefined) {
      return config.max_score
    }

    // Check for max_scores by category and sum them
    if (config.max_scores && typeof config.max_scores === 'object') {
      return Object.values(config.max_scores).reduce<number>(
        (sum, val) => sum + (typeof val === 'number' ? val : 0),
        0
      )
    }

    // Fallback: calculate from scoring_rules if available
    if (config.scoring_rules && typeof config.scoring_rules === 'object') {
      const maxFromRules = Object.values(config.scoring_rules).reduce((sum, rule) => {
        if (rule.max_score !== undefined) {
          return sum + rule.max_score
        }
        return sum
      }, 0)
      if (maxFromRules > 0) return maxFromRules
    }

    // Last resort: use highest threshold value as approximation
    const highestThreshold = Math.max(...Object.values(thresholds.value))
    return highestThreshold > 0 ? highestThreshold * 1.5 : 100
  })

  /**
   * Calculate progress percentage (0-100)
   */
  const progressPercentage = computed<number>(() => {
    const max = maxScore.value
    if (max === 0) return 0

    const percentage = (totalScore.value / max) * 100
    return Math.min(Math.max(percentage, 0), 100)
  })

  return {
    totalScore,
    categoryScores,
    classification,
    classificationColor,
    nearThreshold,
    maxScore,
    progressPercentage
  }
}
