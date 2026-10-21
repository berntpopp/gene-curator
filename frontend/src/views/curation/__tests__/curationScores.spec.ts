import { describe, it, expect } from 'vitest'
import { storedScores } from '../curationScores'

const ct = (key: string, score: number, types: [string, number][] = []) => ({
  key,
  score,
  types: types.map(([path, s]) => ({ path: `${key}.${path}`, score: s }))
})

describe('storedScores', () => {
  it('maps stored totals and the trace onto the breakdown', () => {
    const s = storedScores({
      total_score: 9.6,
      genetic_evidence_total: 8.6,
      experimental_evidence_total: 1,
      trace: {
        sections: [
          {
            key: 'genetic_evidence',
            score: 8.6,
            cap: 12,
            categories: [
              ct('case_level', 5.6, [
                ['autosomal_dominant_or_x_linked.predicted_or_proven_null', 3],
                ['autosomal_dominant_or_x_linked.other_variant_type', 1],
                ['autosomal_recessive.predicted_or_proven_null', 1.5],
                ['autosomal_recessive.other_variant_type', 0.1]
              ]),
              ct('segregation', 2),
              ct('case_control', 1)
            ]
          },
          {
            key: 'experimental_evidence',
            score: 1,
            categories: [
              ct('function', 0.5, [
                ['biochemical_function', 0.5],
                ['protein_interaction', 0.2],
                ['expression', 0.3]
              ]),
              ct('functional_alteration', 0.25),
              ct('models', 1),
              ct('rescue', 0.75)
            ]
          }
        ]
      }
    })
    expect(s).toEqual({
      caseLevel: { adxlNull: 3, adxlOther: 1, arNull: 1.5, arOther: 0.1 },
      caseLevelTotal: 5.6,
      functionTotal: 0.5,
      segregation: 2,
      caseControl: 1,
      genetic: 8.6,
      function: { biochemical: 0.5, proteinInteraction: 0.2, expression: 0.3 },
      functionalAlteration: 0.25,
      models: 1,
      rescue: 0.75,
      experimental: 1,
      total: 9.6,
      caps: { genetic: 12, experimental: null },
      traced: true
    })
  })

  it('reads zero for missing scores or trace', () => {
    expect(storedScores(undefined).total).toBe(0)
    const legacy = storedScores({ total_score: 3 })
    expect(legacy.caseLevel.adxlNull).toBe(0)
    expect(legacy).toMatchObject({ traced: false, caps: { genetic: null, experimental: null } })
  })

  it('splits a shared Models & Rescue category without exceeding its cap (#420)', () => {
    const s = storedScores({
      trace: {
        sections: [
          {
            key: 'experimental_evidence',
            score: 4,
            categories: [
              {
                key: 'models_and_rescue',
                score: 4,
                types: [
                  { path: 'models.non_human_model_organism', score: 4 },
                  { path: 'rescue.human', score: 2 },
                  { path: 'rescue.cell_culture', score: 1 }
                ]
              }
            ]
          }
        ]
      }
    })
    // 7 raw points under a cap of 4: models first, rescue gets what the cap leaves
    expect([s.models, s.rescue]).toEqual([4, 0])
  })

  it('reads each kind of a shared category below the cap', () => {
    const s = storedScores({
      trace: {
        sections: [
          {
            key: 'experimental_evidence',
            score: 3,
            categories: [
              {
                key: 'models_and_rescue',
                score: 3,
                types: [
                  { path: 'models.cell_culture_model', score: 1 },
                  { path: 'rescue.patient_cells', score: 2 }
                ]
              }
            ]
          }
        ]
      }
    })
    expect([s.models, s.rescue]).toEqual([1, 2])
  })
})
