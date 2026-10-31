import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime, formatVersion, EMPTY } from '../format'

describe('format', () => {
  it('prefixes v only to a numeric version', () => {
    expect(formatVersion('1.0.0')).toBe('v1.0.0')
    expect(formatVersion('alpha')).toBe('alpha')
    expect(formatVersion('SOP v11')).toBe('SOP v11')
    expect(formatVersion(null)).toBe(EMPTY)
  })
  it('formats timestamps in local time (built from local parts, TZ-independent)', () => {
    const d = new Date(2026, 9, 20, 14, 2, 33)
    expect(formatDate(d)).toBe('2026-10-20')
    expect(formatDateTime(d)).toBe('2026-10-20 14:02')
    expect(formatDateTime(d.toISOString())).toBe('2026-10-20 14:02')
  })
  it('passes date-only strings through unshifted', () => {
    expect(formatDate('2026-10-20')).toBe('2026-10-20')
    expect(formatDateTime('2026-10-20')).toBe('2026-10-20')
  })
  it.each([null, undefined, '', 'garbage'])('returns the empty marker for %s', v => {
    expect(formatDate(v)).toBe('—')
    expect(formatDateTime(v)).toBe(EMPTY)
  })
})
