import { describe, it, expect } from 'vitest'
import { clientPage, relativeTime } from '../tableRows'

describe('relativeTime', () => {
  const now = new Date('2026-10-20T12:00:00Z').getTime()
  const ago = (ms: number) => new Date(now - ms).toISOString()

  it('names the age within a week and the date after', () => {
    expect(relativeTime(null, now)).toBe('unknown')
    expect(relativeTime(ago(10_000), now)).toBe('just now')
    expect(relativeTime(ago(5 * 60_000), now)).toBe('5m ago')
    expect(relativeTime(ago(3 * 3_600_000), now)).toBe('3h ago')
    expect(relativeTime(ago(2 * 86_400_000), now)).toBe('2d ago')
    expect(relativeTime('2026-10-01', now)).toBe('2026-10-01')
  })
})

describe('clientPage', () => {
  const rows = [
    { g: 'PKD1', n: 2 },
    { g: 'ACTA2', n: 10 },
    { g: 'BRCA1', n: 1 }
  ]
  const page = (sortBy: { key: string; order: 'asc' | 'desc' }[], p = 1, size = 2) =>
    clientPage(rows, { sortBy, page: p, itemsPerPage: size })

  it('keeps the given order unsorted and slices the page', () => {
    expect(page([]).map(r => r.g)).toEqual(['PKD1', 'ACTA2'])
    expect(page([], 2).map(r => r.g)).toEqual(['BRCA1'])
  })

  it('sorts text and numbers in either direction', () => {
    expect(page([{ key: 'g', order: 'asc' }], 1, 3).map(r => r.g)).toEqual([
      'ACTA2',
      'BRCA1',
      'PKD1'
    ])
    expect(page([{ key: 'n', order: 'desc' }], 1, 3).map(r => r.n)).toEqual([10, 2, 1])
    expect(rows[0]!.g).toBe('PKD1') // input untouched
  })
})
