import { describe, it, expect } from 'vitest'
import { getAvatarColor, getInitials } from '../curatorDisplay'
import { getValidationClass, getValidationColor, getValidationIcon } from '../bulkValidationDisplay'

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

describe('bulkValidationDisplay', () => {
  it('maps valid, suggestion and not_found statuses', () => {
    expect(getValidationClass('valid')).toBe('bg-success-lighten-5')
    expect(getValidationClass('suggestion')).toBe('bg-warning-lighten-5')
    expect(getValidationClass('not_found')).toBe('bg-error-lighten-5')
    expect(getValidationColor('valid')).toBe('success')
    expect(getValidationColor('suggestion')).toBe('warning')
    expect(getValidationColor('not_found')).toBe('error')
    expect(getValidationIcon('valid')).toBe('mdi-check-circle')
    expect(getValidationIcon('suggestion')).toBe('mdi-help-circle')
    expect(getValidationIcon('not_found')).toBe('mdi-close-circle')
  })

  it('falls back for unknown statuses', () => {
    expect(getValidationClass('other')).toBe('')
    expect(getValidationColor('other')).toBe('grey')
    expect(getValidationIcon('other')).toBe('mdi-circle-outline')
  })
})
