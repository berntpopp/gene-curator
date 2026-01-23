import { describe, it, expect } from 'vitest'
import { ref, nextTick } from 'vue'
import { useSchemaScoring } from '../useSchemaScoring'

describe('useSchemaScoring', () => {
  // Test data for different scoring engines
  const clingenScores = {
    genetic_evidence_score: 8,
    experimental_evidence_score: 4
  }

  const clingenConfig = {
    engine: 'clingen',
    max_score: 18,
    classification_thresholds: {
      Definitive: 12,
      Strong: 7,
      Moderate: 2,
      Limited: 0.1
    }
  }

  const genccConfig = {
    engine: 'gencc',
    max_score: 8,
    classification_thresholds: {
      Definitive: 7,
      Strong: 5,
      Moderate: 3,
      Limited: 1
    }
  }

  describe('totalScore calculation', () => {
    it('returns 0 when scoreCalculations is null', () => {
      const scores = ref(null)
      const config = ref(clingenConfig)
      const { totalScore } = useSchemaScoring(scores, config)
      expect(totalScore.value).toBe(0)
    })

    it('sums score_calculations values correctly', () => {
      const scores = ref(clingenScores)
      const config = ref(clingenConfig)
      const { totalScore } = useSchemaScoring(scores, config)
      expect(totalScore.value).toBe(12)
    })

    it('includes all numeric values in summation', () => {
      const scores = ref({ category_a: 5, category_b: 3, category_c: 2 })
      const config = ref(clingenConfig)
      const { totalScore } = useSchemaScoring(scores, config)
      expect(totalScore.value).toBe(10)
    })
  })

  describe('classification derivation', () => {
    it('returns Definitive for score >= 12 (ClinGen)', () => {
      const scores = ref({ total_score: 12 })
      const config = ref(clingenConfig)
      const { classification } = useSchemaScoring(scores, config)
      expect(classification.value).toBe('Definitive')
    })

    it('returns Strong for score >= 7 and < 12', () => {
      const scores = ref({ total_score: 8 })
      const config = ref(clingenConfig)
      const { classification } = useSchemaScoring(scores, config)
      expect(classification.value).toBe('Strong')
    })

    it('returns Moderate for score >= 2 and < 7', () => {
      const scores = ref({ total_score: 4 })
      const config = ref(clingenConfig)
      const { classification } = useSchemaScoring(scores, config)
      expect(classification.value).toBe('Moderate')
    })

    it('returns Limited for score >= 0.1 and < 2', () => {
      const scores = ref({ total_score: 1 })
      const config = ref(clingenConfig)
      const { classification } = useSchemaScoring(scores, config)
      expect(classification.value).toBe('Limited')
    })

    it('returns Limited for score < 0.1', () => {
      const scores = ref({ total_score: 0 })
      const config = ref(clingenConfig)
      const { classification } = useSchemaScoring(scores, config)
      expect(classification.value).toBe('Limited')
    })

    it('works with GenCC thresholds', () => {
      const scores = ref({ total_score: 5 })
      const config = ref(genccConfig)
      const { classification } = useSchemaScoring(scores, config)
      expect(classification.value).toBe('Strong')
    })
  })

  describe('classificationColor', () => {
    it('returns success for Definitive', () => {
      const scores = ref({ total_score: 15 })
      const config = ref(clingenConfig)
      const { classificationColor } = useSchemaScoring(scores, config)
      expect(classificationColor.value).toBe('success')
    })

    it('returns success for Strong', () => {
      const scores = ref({ total_score: 8 })
      const config = ref(clingenConfig)
      const { classificationColor } = useSchemaScoring(scores, config)
      expect(classificationColor.value).toBe('success')
    })

    it('returns info for Moderate', () => {
      const scores = ref({ total_score: 4 })
      const config = ref(clingenConfig)
      const { classificationColor } = useSchemaScoring(scores, config)
      expect(classificationColor.value).toBe('info')
    })

    it('returns warning for Limited', () => {
      const scores = ref({ total_score: 1 })
      const config = ref(clingenConfig)
      const { classificationColor } = useSchemaScoring(scores, config)
      expect(classificationColor.value).toBe('warning')
    })

    it('returns warning for Limited at score 0', () => {
      const scores = ref({ total_score: 0 })
      const config = ref(clingenConfig)
      const { classificationColor } = useSchemaScoring(scores, config)
      expect(classificationColor.value).toBe('warning')
    })
  })

  describe('nearThreshold detection', () => {
    it('returns true when within 1 point of next threshold', () => {
      const scores = ref({ total_score: 6.5 }) // 0.5 from Strong (7)
      const config = ref(clingenConfig)
      const { nearThreshold } = useSchemaScoring(scores, config)
      expect(nearThreshold.value).toBe(true)
    })

    it('returns false when not near threshold', () => {
      const scores = ref({ total_score: 4 }) // 3 from Strong (7)
      const config = ref(clingenConfig)
      const { nearThreshold } = useSchemaScoring(scores, config)
      expect(nearThreshold.value).toBe(false)
    })
  })

  describe('progressPercentage', () => {
    it('calculates percentage correctly', () => {
      const scores = ref({ total_score: 9 })
      const config = ref(clingenConfig) // max_score: 18
      const { progressPercentage } = useSchemaScoring(scores, config)
      expect(progressPercentage.value).toBe(50)
    })

    it('caps at 100%', () => {
      const scores = ref({ total_score: 20 })
      const config = ref(clingenConfig)
      const { progressPercentage } = useSchemaScoring(scores, config)
      expect(progressPercentage.value).toBe(100)
    })
  })

  describe('reactivity', () => {
    it('updates when scores change', async () => {
      const scores = ref({ total_score: 5 })
      const config = ref(clingenConfig)
      const { classification } = useSchemaScoring(scores, config)
      expect(classification.value).toBe('Moderate')

      scores.value = { total_score: 12 }
      await nextTick()
      expect(classification.value).toBe('Definitive')
    })
  })
})
