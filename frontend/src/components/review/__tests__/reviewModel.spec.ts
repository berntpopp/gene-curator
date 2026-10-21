import { describe, it, expect } from 'vitest'
import {
  groupDiff,
  itemKey,
  itemLabel,
  itemState,
  formatValue,
  approveBlockers,
  queryTodos,
  checklistFor
} from '../reviewModel'
import type { Schema } from '@/types/api'

type Item = Schema<'DiffItem'>
type Comment = Schema<'ReviewComment'>

const c = (o: Partial<Comment>): Comment => ({
  id: `c${Math.random()}`,
  curation_id: 'cur',
  review_id: null,
  item_path: 'genetic_evidence.case_level[a]',
  body: '',
  author_id: 'bob',
  status: 'open',
  kind: 'query',
  created_at: '2026-10-20T10:00:00Z',
  updated_at: '2026-10-20T10:00:00Z',
  ...o
})

describe('itemKey / itemLabel', () => {
  it('groups fields of a list record under the record, scalars stay their own item', () => {
    expect(itemKey('genetic_evidence.case_level[a1].points')).toBe(
      'genetic_evidence.case_level[a1]'
    )
    expect(itemKey('genetic_evidence.case_level[a1]')).toBe('genetic_evidence.case_level[a1]')
    expect(itemKey('evidence_summary')).toBe('evidence_summary')
  })

  it('makes readable labels', () => {
    expect(itemLabel('genetic_evidence.case_level[a1]')).toBe('Genetic evidence › Case level [a1]')
    expect(itemLabel('evidence_summary')).toBe('Evidence summary')
  })
})

describe('groupDiff', () => {
  const items: Item[] = [
    { path: 'g.cases[a].points', change: 'changed', before: 1.5, after: 2 },
    { path: 'g.cases[a].explanation', change: 'added', before: null, after: 'splice assay' },
    { path: 'g.cases[b]', change: 'added', before: null, after: { pmid: '1' } },
    { path: 'summary', change: 'changed', before: 'x', after: 'y' }
  ]
  const groups = groupDiff(items)

  it('collects field rows per item in first-seen order', () => {
    expect(groups.map(g => g.key)).toEqual(['g.cases[a]', 'g.cases[b]', 'summary'])
    expect(groups[0]!.fields.map(f => f.name)).toEqual(['points', 'explanation'])
  })

  it('classifies an item as added, removed or changed', () => {
    expect(groups[0]!.change).toBe('changed')
    expect(groups[1]!.change).toBe('added')
    expect(groups[1]!.fields[0]!.name).toBe('')
  })
})

describe('formatValue', () => {
  it('renders scalars, objects and nothing', () => {
    expect(formatValue(null)).toBe('none')
    expect(formatValue(undefined)).toBe('none')
    expect(formatValue(2)).toBe('2')
    expect(formatValue('abc')).toBe('abc')
    expect(formatValue({ a: 1 })).toBe('{"a":1}')
  })
})

describe('itemState', () => {
  const path = 'g.cases[a]'
  it('is unreviewed without comments', () => {
    expect(itemState([], path, 'bob')).toEqual({
      status: 'unreviewed',
      queries: [],
      accepted: null
    })
  })

  it('is accepted by my open accepted row, ignoring other reviewers and withdrawn ones', () => {
    const mine = c({ item_path: path, kind: 'accepted' })
    expect(itemState([mine], path, 'bob').status).toBe('accepted')
    expect(
      itemState([c({ item_path: path, kind: 'accepted', author_id: 'carl' })], path, 'bob').status
    ).toBe('unreviewed')
    expect(itemState([{ ...mine, status: 'resolved' }], path, 'bob').status).toBe('unreviewed')
  })

  it('is queried while a query is open, answered once all are resolved', () => {
    const open = c({ item_path: path })
    expect(itemState([open], path, 'bob').status).toBe('queried')
    expect(itemState([{ ...open, status: 'resolved' }], path, 'bob').status).toBe('answered')
  })
})

describe('approveBlockers', () => {
  const groups = groupDiff([
    { path: 'g.a[1].x', change: 'changed', before: 1, after: 2 },
    { path: 'g.b[2]', change: 'added', before: null, after: 1 }
  ])
  it('lists items that are neither accepted nor resolved', () => {
    expect(approveBlockers(groups, [], 'bob')).toHaveLength(2)
    const comments = [c({ item_path: 'g.a[1]', kind: 'accepted' }), c({ item_path: 'g.b[2]' })]
    expect(approveBlockers(groups, comments, 'bob').map(b => b.key)).toEqual(['g.b[2]'])
    expect(
      approveBlockers(groups, [comments[0]!, { ...comments[1]!, status: 'resolved' }], 'bob')
    ).toEqual([])
  })
})

describe('queryTodos', () => {
  it('turns open queries into a to-do list for the curator', () => {
    const text = queryTodos([
      c({ item_path: 'g.a[1]', body: 'Check gnomAD' }),
      c({ item_path: 'g.a[1]', body: 'resolved one', status: 'resolved' }),
      c({ item_path: 'summary', body: 'Explain' }),
      c({ item_path: 'g.b[2]', kind: 'accepted' })
    ])
    expect(text).toBe('- G › A [1]: Check gnomAD\n- Summary: Explain')
  })
  it('is empty without open queries', () => {
    expect(queryTodos([])).toBe('')
  })
})

describe('checklistFor', () => {
  it('adds the replication check for Definitive only', () => {
    expect(checklistFor('Strong').map(i => i.id)).toEqual([
      'publication',
      'points',
      'contradictory'
    ])
    expect(checklistFor('Definitive').map(i => i.id)).toContain('replication')
  })
})
