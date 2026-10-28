import { describe, it, expect } from 'vitest'
import { scoreSnapshot } from '../scorePreview'
import { storedScores } from '@/views/curation/curationScores'
describe('scoreSnapshot', () => {
  it('uses the same presentation values as saved scores without inferring a verdict', () => {
    const calc = { total_score: 7, verdict: 'Custom verdict', trace: { sections: [] } }
    expect(scoreSnapshot(calc, true)).toEqual({
      ...storedScores(calc),
      classification: 'Custom verdict',
      hasContradictory: true,
      excluded: []
    })
  })
  it('names each row that scores 0 by its label and says whether submit refuses it', () => {
    const rows = 'genetic_evidence.case_level.autosomal_recessive.predicted_or_proven_null'
    const evidence = {
      genetic_evidence: {
        case_level: { autosomal_recessive: { predicted_or_proven_null: [{ proband_label: 'P1' }] } }
      }
    }
    const calc = {
      verdict: 'Limited',
      excluded: [
        { path: `${rows}[0]`, field: 'variant_1', reason: 'no_variant' },
        { path: `${rows}[1]`, field: 'variant_1', reason: 'placeholder_variant' },
        { path: `${rows}[2]`, field: 'score_status', reason: 'not_scored' },
        { path: `${rows}[3]`, field: 'pmid', reason: 'unknown_pmid' }
      ]
    }
    const row = 'Genetic evidence › case level › autosomal recessive › predicted or proven null'
    expect(scoreSnapshot(calc, false, evidence)?.excluded).toEqual([
      { text: 'P1 scores 0: needs a variant', refused: true },
      {
        text: `${row} #2 scores 0: needs a real variant (HGVS c./p./g., an rsID or a genomic coordinate)`,
        refused: true
      },
      { text: `${row} #3 scores 0: not scored (status review or contradicts)`, refused: false },
      { text: `${row} #4 scores 0: unknown pmid`, refused: false }
    ])
  })
  it('keeps qualitative totals unavailable', () => {
    expect(scoreSnapshot({ verdict: 'Supportive' }, false)?.total).toBeNull()
  })
  it('shows nothing until the backend returned a verdict', () => {
    for (const input of [undefined, null, [], { total_score: 1 }, { verdict: '' }])
      expect(scoreSnapshot(input, false)).toBeNull()
  })
})
