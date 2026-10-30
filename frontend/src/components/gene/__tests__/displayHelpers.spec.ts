import { describe, it, expect } from 'vitest'
import { getAvatarColor, getInitials } from '../curatorDisplay'

describe('curatorDisplay', () => {
  it('derives a stable avatar colour from the email', () => {
    expect(getAvatarColor('a@example.org')).toBe(getAvatarColor('a@example.org'))
    expect(['primary', 'secondary', 'success', 'info', 'warning', 'error']).toContain(
      getAvatarColor('a@example.org')
    )
  })

  it('returns the first colour for a missing email', () => {
    expect(getAvatarColor(null)).toBe('primary')
    expect(getAvatarColor(undefined)).toBe('primary')
  })

  it('builds initials from first and last name parts', () => {
    expect(getInitials('Ada Lovelace')).toBe('AL')
    expect(getInitials('  grace  ')).toBe('G')
    expect(getInitials('Ada Byron King')).toBe('AK')
  })

  it('uses ? when there is no name', () => {
    expect(getInitials('')).toBe('?')
    expect(getInitials(null)).toBe('?')
  })
})
