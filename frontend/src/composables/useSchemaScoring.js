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

export function useSchemaScoring(scoreCalculations, scoringConfiguration) {
  /**
   * Calculate total score by summing all score_calculations values
   */
  const totalScore = computed(() => {
    if (!scoreCalculations.value) return 0

    // Sum all numeric values in score_calculations
    return Object.values(scoreCalculations.value).reduce((sum, value) => {
      const numValue = typeof value === 'number' ? value : 0
      return sum + numValue
    }, 0)
  })

  /**
   * Extract category scores (all score_calculations entries)
   */
  const categoryScores = computed(() => {
    if (!scoreCalculations.value) return {}
    return { ...scoreCalculations.value }
  })

  /**
   * Get classification thresholds from scoring configuration
   */
  const thresholds = computed(() => {
    return scoringConfiguration.value?.classification_thresholds || {}
  })

  /**
   * Determine classification based on total score and thresholds
   * Returns the highest classification level that the score meets
   */
  const classification = computed(() => {
    const score = totalScore.value
    const thresh = thresholds.value

    if (!thresh || Object.keys(thresh).length === 0) {
      return null
    }

    // Sort thresholds by value (descending) to check highest first
    const sortedLevels = Object.entries(thresh)
      .sort(([, a], [, b]) => b - a)

    // Find first threshold that score meets or exceeds
    for (const [level, requiredScore] of sortedLevels) {
      if (score >= requiredScore) {
        return level
      }
    }

    // If no threshold met, return lowest classification or null
    return sortedLevels.length > 0 ? sortedLevels[sortedLevels.length - 1][0] : null
  })

  /**
   * Get Vuetify color for classification
   * Maps common classification levels to semantic colors
   */
  const classificationColor = computed(() => {
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
  const nearThreshold = computed(() => {
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
    return (nextThreshold - score) <= 1
  })

  /**
   * Get maximum possible score from scoring configuration
   * Falls back to dynamic calculation from max_scores if available
   */
  const maxScore = computed(() => {
    const config = scoringConfiguration.value

    if (!config) return 0

    // Check for explicit max_score
    if (config.max_score !== undefined) {
      return config.max_score
    }

    // Check for max_scores by category and sum them
    if (config.max_scores && typeof config.max_scores === 'object') {
      return Object.values(config.max_scores).reduce((sum, val) => {
        return sum + (typeof val === 'number' ? val : 0)
      }, 0)
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
    const highestThreshold = Math.max(...Object.values(thresholds.value || {}))
    return highestThreshold > 0 ? highestThreshold * 1.5 : 100
  })

  /**
   * Calculate progress percentage (0-100)
   */
  const progressPercentage = computed(() => {
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
