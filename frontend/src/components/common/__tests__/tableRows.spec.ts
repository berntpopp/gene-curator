import { describe, it, expect } from 'vitest'
import { relativeTime } from '../tableRows'

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
