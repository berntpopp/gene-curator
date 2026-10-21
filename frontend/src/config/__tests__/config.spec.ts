import { describe, it, expect } from 'vitest'
import terminologyDefault, { TERMINOLOGY, getTermLabel, isDeprecated } from '../terminology'

describe('terminology', () => {
  it('returns the display label for a known key', () => {
    expect(getTermLabel('ASSIGNMENT')).toBe(TERMINOLOGY.ASSIGNMENT)
    expect(getTermLabel('COMPLETED')).toBe('Completed')
  })

  it('falls back to the key itself for unknown terms', () => {
    expect(getTermLabel('NOT_A_TERM')).toBe('NOT_A_TERM')
  })

  it('flags deprecated terminology keys only', () => {
    expect(isDeprecated('GENE_ASSIGNMENT')).toBe(true)
    expect(isDeprecated('BROWSE')).toBe(true)
    expect(isDeprecated('ASSIGNMENT')).toBe(false)
  })

  it('uses one noun per concept for nav labels and page titles', () => {
    expect(TERMINOLOGY.GENE_CATALOG).toBe('Gene Catalogue')
    expect(TERMINOLOGY.SCOPES).toBe('Scopes')
    expect(TERMINOLOGY.SIGN_IN).toBe('Sign in')
    expect(isDeprecated('GENES')).toBe(false)
  })

  it('default export is the terminology table', () => {
    expect(terminologyDefault).toBe(TERMINOLOGY)
  })
})
