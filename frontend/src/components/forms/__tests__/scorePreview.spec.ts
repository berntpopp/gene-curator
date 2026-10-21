import { describe, it, expect } from 'vitest'
import { scoreSnapshot } from '../scorePreview'

const preview = (sections: unknown[]) => ({
  curation_id: 'c1',
  total_score: 7,
  classification: 'Moderate',
  genetic_score: 5,
  experimental_score: 2,
  calculated_at: '2026-10-21T00:00:00Z',
  breakdown: { trace: { sections } }
})

describe('scoreSnapshot', () => {
  it('reads capped category scores from the trace', () => {
    const s = scoreSnapshot(
      preview([
        { key: 'genetic_evidence', categories: [{ key: 'case_level', score: 4 }] },
        { key: 'experimental_evidence', categories: [{ key: 'models', score: 2 }] }
      ]),
      true
    )
    expect(s).toMatchObject({
      total: 7,
      classification: 'Moderate',
      hasContradictory: true,
      geneticBreakdown: { caseLevel: 4, segregation: 0 },
      experimentalBreakdown: { models: 2, rescue: 0 }
    })
  })

  it('splits a shared Models & Rescue category into its kinds', () => {
    const s = scoreSnapshot(
      preview([
        {
          key: 'experimental_evidence',
          categories: [
            {
              key: 'models_and_rescue',
              score: 4,
              types: [
                { path: 'models.non_human_model_organism', score: 2 },
                { path: 'rescue.human', score: 2 },
                { path: 'rescue.cell_culture', score: 1 }
              ]
            }
          ]
        }
      ]),
      false
    )
    expect(s.experimentalBreakdown).toMatchObject({ models: 2, rescue: 3 })
  })

  it('reads zeros from a preview without a trace', () => {
    const s = scoreSnapshot({ ...preview([]), breakdown: {} }, false)
    expect(s.geneticBreakdown).toEqual({ caseLevel: 0, segregation: 0, caseControl: 0 })
  })
})
