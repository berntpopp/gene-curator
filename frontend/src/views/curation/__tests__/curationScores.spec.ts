import { describe, it, expect } from 'vitest'
import { storedScores, warningText } from '../curationScores'

describe('storedScores', () => {
  it('preserves arbitrary categories and historical separate caps without recalculating', () => {
    const trace = {
      raw_total: 6,
      total: 6,
      total_cap: 9,
      class: 'custom',
      sections: [
        {
          key: 'custom_section',
          raw: 6,
          score: 6,
          cap: 8,
          categories: [
            { key: 'models', raw: 4, score: 4, cap: 4, types: [] },
            { key: 'rescue', raw: 2, score: 2, cap: 2, types: [] }
          ]
        }
      ]
    }
    expect(storedScores({ total_score: 6, trace })).toMatchObject({ total: 6, trace })
  })
  it('keeps missing totals unknown and zero explicit', () => {
    expect(storedScores(undefined).total).toBeNull()
    expect(storedScores({ total_score: 0 }).total).toBe(0)
    expect(storedScores({ arbitrary_score: 8 }).total).toBeNull()
    expect(storedScores({ total_score: 3 }).trace).toBeNull()
  })
  it('narrows malformed and older JSON without coercing values into scores', () => {
    for (const input of [null, [], 2, { total_score: '3' }, { total_score: Infinity }]) {
      expect(storedScores(input).total).toBeNull()
    }
    expect(
      storedScores({
        trace: { sections: [null, {}, { categories: [null, { types: [null, {}] }] }] }
      }).trace?.sections
    ).toHaveLength(2)
    expect(storedScores({ trace: [] }).trace).toBeNull()
  })
})

describe('warningText (MUI-18)', () => {
  it('names review flags and evidence rows for people', () => {
    expect(warningText('review_flags.band_margin: the total of 6 points is near')).toBe(
      'Near a class boundary: the total of 6 points is near'
    )
    expect(warningText('review_flags.new_flag: x')).toBe('New flag: x')
    expect(warningText('genetic.probands[0].points = 5 is above')).toBe(
      'Genetic › probands #1 › Points = 5 is above'
    )
    expect(warningText('plain text')).toBe('plain text')
  })
})
