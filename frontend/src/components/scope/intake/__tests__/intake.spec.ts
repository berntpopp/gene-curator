import { describe, it, expect } from 'vitest'
import { parseSymbols, reasonText, toRows } from '../intake'
import type { Schema } from '@/types/api'

type Item = Schema<'GeneResolveItem'>
const cand = { hgnc_id: 'HGNC:1', symbol: 'A1', name: 'a', gene_id: null }

describe('parseSymbols', () => {
  it('splits on newlines, commas, semicolons, tabs and spaces', () => {
    expect(parseSymbols('PKD1, PKD2;\tUMOD\nHGNC:1  NPHS1\n')).toEqual([
      'PKD1',
      'PKD2',
      'UMOD',
      'HGNC:1',
      'NPHS1'
    ])
    expect(parseSymbols('  ')).toEqual([])
  })
})

describe('toRows', () => {
  const items: Item[] = [
    { input: 'A1', index: 0, status: 'resolved', match_type: 'symbol', candidates: [cand] },
    { input: 'a1', index: 1, status: 'resolved', candidates: [cand], duplicate_of: 0 },
    {
      input: 'X',
      index: 2,
      status: 'ambiguous',
      candidates: [cand, { ...cand, hgnc_id: 'HGNC:2' }]
    },
    { input: 'Z', index: 3, status: 'not_found', reason: 'lookup_cap' },
    { input: 'Q', index: 4, status: 'not_found', duplicate_of: 9 }
  ]
  const rows = toRows(items)

  it('includes resolved rows, not duplicates, ambiguous or missing ones', () => {
    expect(rows.map(r => r.include)).toEqual([true, false, false, false, false])
    expect(rows[0]!.pick).toEqual(cand)
    expect(rows[2]!.pick).toBeNull()
  })

  it('names the earlier input a duplicate repeats, falling back to its index', () => {
    expect(rows[1]!.duplicateOf).toBe('A1')
    expect(rows[4]!.duplicateOf).toBe('9')
    expect(rows[0]!.duplicateOf).toBeNull()
  })

  it('states honestly why an entry was not looked up', () => {
    expect(reasonText(items[3]!)).toContain('too many')
    expect(reasonText({ ...items[3]!, reason: 'lookup_timeout' })).toContain('in time')
    expect(reasonText({ ...items[3]!, reason: null })).toBe('Not found at HGNC')
    expect(reasonText({ ...items[3]!, reason: 'invalid_identifier' })).toBe(
      'Not a gene symbol or HGNC ID'
    )
  })
})
