import { describe, it, expect } from 'vitest'
import { stageOf, stageTitle } from '../geneStage'

describe('stageOf', () => {
  it.each([
    [false, null, null, 'unassigned'],
    [true, null, null, 'precuration'],
    [false, { status: 'draft' }, null, 'precuration'],
    [true, { status: 'approved' }, null, 'curation'],
    [true, null, { status: 'draft' }, 'curation'],
    [true, null, { status: 'submitted' }, 'review'],
    [true, null, { status: 'in_review' }, 'review'],
    [true, null, { status: 'active' }, 'active']
  ] as const)('curator %s, pre %j, cur %j -> %s', (c, pre, cur, expected) => {
    expect(stageOf(c, pre, cur)).toBe(expected)
  })

  it('titles stages', () => {
    expect(stageTitle('review')).toBe('In review')
  })
})
