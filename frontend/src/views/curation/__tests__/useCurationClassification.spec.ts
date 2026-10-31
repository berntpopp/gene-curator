import { describe, it, expect } from 'vitest'
import { useCurationClassification } from '../useCurationClassification'

describe('useCurationClassification', () => {
  it('reads the stored total and labels the stored verdict', () => {
    const { scores, classification } = useCurationClassification(() => ({
      computed_scores: { total_score: 9.6 },
      computed_verdict: 'moderate'
    }))
    expect(scores.value.total).toBe(9.6)
    expect(classification.value).toBe('Moderate')
  })

  it('is empty and unavailable before the curation has been scored', () => {
    const { scores, classification } = useCurationClassification(() => null)
    expect(scores.value.total).toBeNull()
    expect(classification.value).toBe('')
  })

  it('labels the final classification, the calculated one without an override', () => {
    const c = {
      computed_verdict: 'moderate',
      final_classification: 'Disputed',
      curator_classification_rationale: 'Contradicting cohort'
    }
    const { classification, final, rationale } = useCurationClassification(() => c)
    expect([classification.value, final.value, rationale.value]).toEqual([
      'Moderate',
      'Disputed',
      'Contradicting cohort'
    ])
    const plain = useCurationClassification(() => ({ computed_verdict: 'moderate' }))
    expect([plain.final.value, plain.rationale.value]).toEqual(['Moderate', ''])
  })

  it("shows the curator's proposal until approval sets the final class (#613)", () => {
    const pending = useCurationClassification(() => ({
      computed_verdict: null,
      curator_classification: 'definitive',
      final_classification: null
    }))
    expect([pending.classification.value, pending.final.value]).toEqual(['', 'Definitive'])
  })
})
