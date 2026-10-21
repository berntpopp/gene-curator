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

  it('is empty and zero before the curation has been scored', () => {
    const { scores, classification } = useCurationClassification(() => null)
    expect(scores.value.total).toBe(0)
    expect(classification.value).toBe('')
  })
})
