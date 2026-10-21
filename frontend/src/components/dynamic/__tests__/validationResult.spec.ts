import { describe, expect, it } from 'vitest'
import { toFormValidation } from '../validationResult'

describe('toFormValidation', () => {
  it('keeps numeric scores and drops the live-score verdict and trace', () => {
    const result = toFormValidation({
      is_valid: true,
      score_calculations: { total_score: 7, verdict: 'moderate', trace: { total: 7 } }
    })
    expect(result.score_calculations).toEqual({ total_score: 7 })
  })
})
