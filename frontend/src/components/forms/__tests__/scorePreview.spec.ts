import { describe, it, expect } from 'vitest'
import { scoreSnapshot } from '../scorePreview'
import { storedScores } from '@/views/curation/curationScores'
describe('scoreSnapshot', () => {
  it('uses the same presentation values as saved scores without inferring a verdict', () => {
    const calc = { total_score: 7, verdict: 'Custom verdict', trace: { sections: [] } }
    expect(scoreSnapshot(calc, true)).toEqual({
      ...storedScores(calc),
      classification: 'Custom verdict',
      hasContradictory: true
    })
  })
  it('keeps qualitative totals unavailable', () => {
    expect(scoreSnapshot({ verdict: 'Supportive' }, false)?.total).toBeNull()
  })
  it('shows nothing until the backend returned a verdict', () => {
    for (const input of [undefined, null, [], { total_score: 1 }, { verdict: '' }])
      expect(scoreSnapshot(input, false)).toBeNull()
  })
})
