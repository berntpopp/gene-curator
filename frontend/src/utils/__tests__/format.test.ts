import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime, EMPTY } from '../format'

describe('format', () => {
  it('formats ISO date and datetime (UTC)', () => {
    expect(formatDate('2026-10-20T14:02:33Z')).toBe('2026-10-20')
    expect(formatDateTime('2026-10-20T14:02:33Z')).toBe('2026-10-20 14:02')
    expect(formatDate(new Date('2026-01-02T00:00:00Z'))).toBe('2026-01-02')
  })
  it.each([null, undefined, '', 'garbage'])('returns the empty marker for %s', v => {
    expect(formatDate(v)).toBe('—')
    expect(formatDateTime(v)).toBe(EMPTY)
  })
})
