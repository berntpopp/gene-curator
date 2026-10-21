import { describe, it, expect } from 'vitest'
import { pluralize } from '../pluralize'

describe('pluralize', () => {
  it('uses the singular only for exactly one', () => {
    expect(pluralize(1, 'admin')).toBe('1 admin')
    expect(pluralize(0, 'admin')).toBe('0 admins')
    expect(pluralize(2, 'gene')).toBe('2 genes')
  })
})
