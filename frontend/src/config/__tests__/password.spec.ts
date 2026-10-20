import { describe, it, expect } from 'vitest'
import { passwordRules, PASSWORD_MIN_LENGTH } from '../password'

const check = (v: string) => passwordRules.map(r => r(v)).find(r => r !== true) ?? true

describe('passwordRules', () => {
  it('rejects empty and 7 characters, accepts 8 (matches backend min_length=8)', () => {
    expect(PASSWORD_MIN_LENGTH).toBe(8)
    expect(check('')).toBe('Password is required')
    expect(check('1234567')).toBe('Password must be at least 8 characters')
    expect(check('12345678')).toBe(true)
    expect(check('x'.repeat(128))).toBe(true)
    expect(check('x'.repeat(129))).toBe('Password must be at most 128 characters')
  })
})
