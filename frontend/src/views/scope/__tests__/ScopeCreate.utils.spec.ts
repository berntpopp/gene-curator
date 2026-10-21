import { describe, it, expect } from 'vitest'
import { getInitials, displayNameRules, slugify } from '@/views/scope/ScopeCreate.utils'

describe('getInitials', () => {
  it('returns ? for empty names', () => {
    expect(getInitials(null)).toBe('?')
    expect(getInitials('')).toBe('?')
  })
  it('uses the first letter for a single word', () => {
    expect(getInitials('madonna')).toBe('M')
  })
  it('uses first and last word initials', () => {
    expect(getInitials('  Ada Byron Lovelace ')).toBe('AL')
  })
})

describe('displayNameRules', () => {
  it('requires a value, at least 4 and at most 100 characters', () => {
    const [required, minLength, maxLength] = displayNameRules
    expect(required?.('')).toBe('Display name is required')
    expect(minLength?.('abc')).toBe('Minimum 4 characters required')
    expect(minLength?.('abcd')).toBe(true)
    expect(maxLength?.('x'.repeat(101))).toBe('Maximum 100 characters allowed')
    expect(maxLength?.('x'.repeat(100))).toBe(true)
  })
})

describe('slugify', () => {
  it('lowercases, dashes words and drops everything else', () => {
    expect(slugify('Kidney Genetics')).toBe('kidney-genetics')
    expect(slugify('  Ciliopathies -- & Cystic (PKD)! ')).toBe('ciliopathies-cystic-pkd')
    expect(slugify('Ärzte 2')).toBe('rzte-2')
    expect(slugify('')).toBe('')
  })
})
