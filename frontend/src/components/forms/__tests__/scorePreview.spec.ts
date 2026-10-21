import { describe, it, expect } from 'vitest'
import { scoreSnapshot } from '../scorePreview'

const calc = {
  total_score: 7,
  genetic_evidence_total: 5,
  experimental_evidence_total: 2,
  verdict: 'Moderate',
  trace: {
    sections: [
      {
        key: 'genetic_evidence',
        score: 5,
        categories: [
          { key: 'case_level', score: 4 },
          { key: 'segregation', score: 1 }
        ]
      },
      {
        key: 'experimental_evidence',
        score: 2,
        categories: [
          { key: 'function', score: 0.5 },
          {
            key: 'models_and_rescue',
            score: 1.5,
            types: [
              { path: 'models.cell_culture_model', score: 1 },
              { path: 'rescue.human', score: 0.5 }
            ]
          }
        ]
      }
    ]
  }
}

describe('scoreSnapshot', () => {
  it('maps validate-evidence score_calculations onto the score panel', () => {
    expect(scoreSnapshot(calc, true)).toEqual({
      genetic: 5,
      experimental: 2,
      total: 7,
      classification: 'Moderate',
      hasContradictory: true,
      geneticBreakdown: { caseLevel: 4, segregation: 1, caseControl: 0 },
      experimentalBreakdown: { function: 0.5, functionalAlteration: 0, models: 1, rescue: 0.5 }
    })
  })

  it('shows nothing until the backend returned a verdict', () => {
    expect(scoreSnapshot({ total_score: 1 }, false)).toBeNull()
    expect(scoreSnapshot(undefined, false)).toBeNull()
  })
})
