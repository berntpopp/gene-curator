import { describe, it, expect } from 'vitest'
import { useCurationClassification } from '../useCurationClassification'

describe('useCurationClassification', () => {
  it('scores empty evidence as zero and ignores blank contradictory rows', () => {
    const { scores, classification } = useCurationClassification(() => ({
      contradictory_evidence: [{ pmid: '' }]
    }))

    expect(scores.value.total).toBe(0)
    expect(classification.value).not.toBe('Disputed')
  })

  it('disputes on a filled contradictory row', () => {
    const { classification } = useCurationClassification(() => ({
      contradictory_evidence: [{ pmid: '12345678' }]
    }))

    expect(classification.value).toBe('Disputed')
  })
})
