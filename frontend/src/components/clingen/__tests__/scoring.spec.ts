import { describe, expect, it } from 'vitest'
import {
  calculateExperimentalScore,
  calculateGeneticScore,
  classifyScore,
  normalizeLegacy,
  sumPoints,
  sumProbandPoints
} from '../scoring'
import { createEmptyExperimentalEvidence, createEmptyGeneticEvidence } from '../evidenceDefaults'
import type { EvidenceItem, ExperimentalEvidence, GeneticEvidence } from '../types'

describe('sumPoints / sumProbandPoints', () => {
  it('adds numeric and numeric-string points and treats invalid values as zero', () => {
    const items: EvidenceItem[] = [{ points: 1.5 }, { points: '0.5' }, { points: 'n/a' }, {}]
    expect(sumPoints(items)).toBe(2)
  })

  it('reads proband_counted_points for case-level sums', () => {
    const items: EvidenceItem[] = [
      { pmid: '1', proband_counted_points: 1.5, points: 9 },
      { pmid: '2', proband_counted_points: '0.1' }
    ]
    expect(sumProbandPoints(items)).toBeCloseTo(1.6)
  })

  it('does not score a freshly added empty case-level row', () => {
    const fresh = {
      proband_label: '',
      variant_type: 'nonsense',
      variant: '',
      pmid: '',
      score_status: 'score',
      proband_counted_points: 1.5,
      explanation: ''
    }
    expect(sumProbandPoints([fresh])).toBe(0)
    expect(sumProbandPoints([{ ...fresh, variant: 'c.1A>G' }])).toBe(1.5)
  })

  it('returns zero for missing or non-array input', () => {
    expect(sumPoints(undefined)).toBe(0)
    expect(sumProbandPoints(undefined)).toBe(0)
  })
})

describe('calculateGeneticScore', () => {
  it('is zero for an empty evidence structure', () => {
    expect(calculateGeneticScore(createEmptyGeneticEvidence())).toEqual({
      caseLevel: 0,
      segregation: 0,
      caseControl: 0,
      total: 0
    })
  })

  it('sums case-level proband points across AD/XL and AR groups', () => {
    const ge: GeneticEvidence = {
      ...createEmptyGeneticEvidence(),
      case_level: {
        autosomal_dominant_or_x_linked: {
          predicted_or_proven_null: [{ pmid: '1', proband_counted_points: 1.5 }],
          other_variant_type: [{ pmid: '1', proband_counted_points: 0.1 }]
        },
        autosomal_recessive: {
          predicted_or_proven_null: [{ pmid: '1', proband_counted_points: 1.5 }],
          other_variant_type: []
        }
      }
    }
    const result = calculateGeneticScore(ge)
    expect(result.caseLevel).toBeCloseTo(3.1)
    expect(result.total).toBeCloseTo(3.1)
  })

  it('caps each category at its SOP maximum (case-level 12, segregation 3, case-control 6)', () => {
    const many = Array.from({ length: 10 }, () => ({
      pmid: '1',
      proband_counted_points: 2,
      points: 2
    }))
    const ge: GeneticEvidence = {
      case_level: { autosomal_dominant_or_x_linked: { predicted_or_proven_null: many } },
      segregation: many,
      case_control: { single_variant_analysis: many, aggregate_variant_analysis: many }
    }
    expect(calculateGeneticScore(ge)).toEqual({
      caseLevel: 12,
      segregation: 3,
      caseControl: 6,
      total: 12
    })
  })

  it('uses the larger case-control subtotal', () => {
    const ge: GeneticEvidence = {
      case_control: {
        single_variant_analysis: [{ points: 2 }],
        aggregate_variant_analysis: [{ points: 1.5 }]
      }
    }
    expect(calculateGeneticScore(ge).caseControl).toBeCloseTo(2)
  })
})

describe('calculateExperimentalScore', () => {
  it('is zero for an empty evidence structure', () => {
    expect(calculateExperimentalScore(createEmptyExperimentalEvidence()).total).toBe(0)
  })

  it('caps each experimental category at its SOP maximum and the total at 6', () => {
    const many = Array.from({ length: 10 }, () => ({ points: 2 }))
    const exp: ExperimentalEvidence = {
      function: { biochemical_function: many, protein_interaction: many, expression: many },
      functional_alteration: { patient_cells: many, non_patient_cells: many },
      models: { non_human_model_organism: many, cell_culture_model: many },
      rescue: {
        human: many,
        non_human_model_organism: many,
        cell_culture: many,
        patient_cells: many
      }
    }
    expect(calculateExperimentalScore(exp)).toEqual({
      function: 2,
      functionalAlteration: 2,
      models: 4,
      rescue: 4,
      total: 6
    })
  })

  it('sums rescue points from all four rescue sources', () => {
    const exp: ExperimentalEvidence = {
      rescue: { human: [{ points: 1 }], cell_culture: [{ points: '0.5' }] }
    }
    expect(calculateExperimentalScore(exp).rescue).toBeCloseTo(1.5)
  })
})

describe('classifyScore', () => {
  it.each([
    [12, 'Strong'],
    [11.99, 'Moderate'],
    [7, 'Moderate'],
    [6.99, 'Limited'],
    [2, 'Limited'],
    [1.99, 'Limited'],
    [0.1, 'Limited'],
    [0.09, 'No Known Disease Relationship'],
    [0, 'No Known Disease Relationship']
  ])('classifies total %s as %s', (total, expected) => {
    expect(classifyScore(total, false)).toBe(expected)
  })

  it('returns Definitive only for Strong points with replication over time', () => {
    expect(classifyScore(12, false, true)).toBe('Definitive')
    expect(classifyScore(11.99, false, true)).toBe('Moderate')
    expect(classifyScore(18, true, true)).toBe('Disputed')
  })

  it('returns Disputed whenever contradictory evidence is present', () => {
    expect(classifyScore(18, true)).toBe('Disputed')
    expect(classifyScore(0, true)).toBe('Disputed')
  })
})

it('applies category caps before the genetic total', () => {
  expect(calculateGeneticScore({ segregation: [{ points: 20 }] }).total).toBe(3)
})

describe('legacy {points} dicts', () => {
  it('sums a dict as one item and ignores other shapes', () => {
    expect(sumPoints({ count: 1, points: 0.5 })).toBe(0.5)
    expect(sumPoints('junk')).toBe(0)
    expect(sumProbandPoints([{ pmid: '1', proband_counted_points: 1 }, 'x'])).toBe(1)
  })

  it('normalizeLegacy rewrites dicts to lists, leaves lists alone', () => {
    const out = normalizeLegacy({ a: { b: { points: 1 } }, c: [{ points: 2 }], d: 1 })
    expect(out).toEqual({ a: { b: [{ points: 1 }] }, c: [{ points: 2 }], d: 1 })
  })
})
