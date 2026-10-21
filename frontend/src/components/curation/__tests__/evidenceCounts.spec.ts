import { describe, expect, it } from 'vitest'
import { evidenceCountsText } from '../evidenceCounts'

describe('evidenceCountsText', () => {
  it('counts rows per category and distinct PMIDs', () => {
    const text = evidenceCountsText({
      genetic_evidence: {
        case_level: { autosomal_recessive: { other_variant_type: [{ pmid: '1' }, { pmid: '2' }] } },
        segregation: [{ pmid: '2' }]
      },
      experimental_evidence: { models: { cell_culture_model: [{ pmid: '3' }] } },
      contradictory_evidence: [{}]
    })
    expect(text).toBe('Genetic: 3 items · Experimental: 1 item · Contradictory: 1 item · 3 PMIDs')
  })

  it('handles empty evidence', () => {
    expect(evidenceCountsText(null)).toBe(
      'Genetic: 0 items · Experimental: 0 items · Contradictory: 0 items · 0 PMIDs'
    )
  })
})

it('counts a legacy {points} dict as one item', () => {
  expect(
    evidenceCountsText({ experimental_evidence: { models: { count: 1, points: 0.5 } } })
  ).toContain('Experimental: 1 item')
})
