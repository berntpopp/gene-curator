import { describe, it, expect } from 'vitest'
import { computeScores, classifyScores, type EvidenceData } from '@/views/curation/curationScores'

const full: EvidenceData = {
  genetic_evidence: {
    case_level: {
      autosomal_dominant_or_x_linked: {
        predicted_or_proven_null: [{ proband_counted_points: 2 }, { proband_counted_points: 1 }],
        other_variant_type: [{ proband_counted_points: 0.5 }]
      },
      autosomal_recessive: {
        predicted_or_proven_null: [{ proband_counted_points: 1.5 }],
        other_variant_type: [{ proband_counted_points: null }]
      }
    },
    segregation: [{ points: 3 }],
    case_control: {
      single_variant_analysis: [{ points: 1 }],
      aggregate_variant_analysis: [{ points: 2 }]
    }
  },
  experimental_evidence: {
    function: {
      biochemical_function: [{ points: 1 }],
      protein_interaction: [{ points: 0.5 }],
      expression: [{ points: 0.5 }]
    },
    functional_alteration: { patient_cells: [{ points: 1 }], non_patient_cells: [{ points: 0.5 }] },
    models: { non_human_model_organism: [{ points: 1 }], cell_culture_model: [{ points: 0.5 }] },
    rescue: {
      human: [{ points: 1 }],
      non_human_model_organism: [{ points: 0.5 }],
      cell_culture: [{ points: 0.5 }],
      patient_cells: [{ points: 0.5 }]
    }
  }
}

describe('computeScores', () => {
  it('returns zeros for missing or null evidence', () => {
    for (const evidence of [undefined, null, {}]) {
      const scores = computeScores(evidence)
      expect(scores.genetic).toBe(0)
      expect(scores.experimental).toBe(0)
      expect(scores.total).toBe(0)
      expect(scores.caseLevel).toEqual({ adxlNull: 0, adxlOther: 0, arNull: 0, arOther: 0 })
    }
  })

  it('sums each genetic category from the right fields', () => {
    const scores = computeScores(full)
    expect(scores.caseLevel).toEqual({ adxlNull: 3, adxlOther: 0.5, arNull: 1.5, arOther: 0 })
    expect(scores.segregation).toBe(3)
    expect(scores.caseControl).toBe(3)
    // 3 + 0.5 + 1.5 + 0 + 3 + 3 = 11
    expect(scores.genetic).toBe(11)
  })

  it('sums each experimental category', () => {
    const scores = computeScores(full)
    expect(scores.function).toEqual({ biochemical: 1, proteinInteraction: 0.5, expression: 0.5 })
    expect(scores.functionalAlteration).toBe(1.5)
    expect(scores.models).toBe(1.5)
    expect(scores.rescue).toBe(2.5)
    // 1 + 0.5 + 0.5 + 1.5 + 1.5 + 2.5 = 7.5 -> capped at 6
    expect(scores.experimental).toBe(6)
    expect(scores.total).toBe(17)
  })

  it('caps genetic evidence at 12 points', () => {
    const scores = computeScores({
      genetic_evidence: { segregation: [{ points: 20 }] }
    })
    expect(scores.genetic).toBe(12)
    expect(scores.total).toBe(12)
  })

  it('uses points, not proband_counted_points, for segregation and case-control', () => {
    const scores = computeScores({
      genetic_evidence: {
        segregation: [{ points: 2, proband_counted_points: 9 }],
        case_control: { single_variant_analysis: [{ points: null }] }
      }
    })
    expect(scores.segregation).toBe(2)
    expect(scores.caseControl).toBe(0)
  })
})

describe('classifyScores', () => {
  it.each([
    [12, 6, 'Definitive'],
    [12, 4.5, 'Strong'],
    [9, 3, 'Moderate'],
    [1, 0, 'Limited'],
    [0, 0, 'No Known Disease Relationship']
  ])('total %d genetic %d -> %s', (total, genetic, label) => {
    expect(classifyScores(total, genetic)).toBe(label)
  })

  it('does not reach Definitive when genetic is below 6', () => {
    expect(classifyScores(12, 5.5)).toBe('Strong')
  })

  it('does not reach Moderate when total is below 9', () => {
    expect(classifyScores(8, 3)).toBe('Limited')
  })
})
