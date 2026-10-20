import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  sanitizeForLogging,
  sanitizeLogEntry,
  containsSensitiveData,
  testSanitization
} from '../logSanitizer'

describe('logSanitizer', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('sanitizeForLogging', () => {
    it('redacts values under sensitive keys, ignoring case, underscores and dashes', () => {
      const result = sanitizeForLogging({
        accessToken: 'abc',
        Password: 'hunter2',
        api_key: 'k',
        'user-email': 'a@b.co',
        variant: 'c.123A>G',
        name: 'Ada'
      })

      expect(result).toEqual({
        accessToken: '[REDACTED_SENSITIVE]',
        Password: '[REDACTED_SENSITIVE]',
        api_key: '[REDACTED_SENSITIVE]',
        'user-email': '[REDACTED_SENSITIVE]',
        variant: '[REDACTED_SENSITIVE]',
        name: 'Ada'
      })
    })

    it('recurses into nested objects and arrays', () => {
      const result = sanitizeForLogging({
        outer: { inner: { secret: 'x', label: 'keep' } },
        list: [{ email: 'a@b.co' }, 'plain']
      })

      expect(result).toEqual({
        outer: { inner: { secret: '[REDACTED_SENSITIVE]', label: 'keep' } },
        list: [{ email: '[REDACTED_SENSITIVE]' }, 'plain']
      })
    })

    it('stops descending once the depth budget is spent', () => {
      const deep = { a: { b: { c: { d: 'value' } } } }

      expect(sanitizeForLogging(deep, 2)).toEqual({ a: { b: '[MAX_DEPTH_EXCEEDED]' } })
    })

    it('processes at most the first 100 array items', () => {
      const items = Array.from({ length: 150 }, (_, i) => i)

      const result = sanitizeForLogging(items) as number[]

      expect(result).toHaveLength(100)
      expect(result[99]).toBe(99)
    })

    it('passes null, undefined and non-string primitives through unchanged', () => {
      expect(sanitizeForLogging(null)).toBeNull()
      expect(sanitizeForLogging(undefined)).toBeUndefined()
      expect(sanitizeForLogging(42)).toBe(42)
      expect(sanitizeForLogging(true)).toBe(true)
    })

    it('redacts sensitive patterns inside plain string values', () => {
      expect(sanitizeForLogging('mail me at user@example.com')).toBe('mail me at [REDACTED_EMAIL]')
      expect(sanitizeForLogging('NM variant c.123A>G here')).toBe(
        'NM variant [REDACTED_VARIANT] here'
      )
      expect(sanitizeForLogging('protein p.Arg123Trp')).toBe('protein [REDACTED_VARIANT]')
    })

    it('redacts genomic coordinates as coordinates, not as phone numbers', () => {
      expect(sanitizeForLogging('locus chr7:100-200 found')).toBe(
        'locus [REDACTED_COORDINATE] found'
      )
      expect(sanitizeForLogging('chrX:5-9')).toBe('[REDACTED_COORDINATE]')
      expect(sanitizeForLogging('call 555-123-4567 now')).toBe('call [REDACTED_PHONE] now')
    })

    it('leaves strings without special characters untouched', () => {
      expect(sanitizeForLogging('plain text 123')).toBe('plain text 123')
    })

    it('redacts JWT-like strings', () => {
      expect(sanitizeForLogging('bearer aaaaa.bbbbb.ccccc')).toContain('[REDACTED_TOKEN]')
    })

    it('skips pattern work for strings without special characters (quick check)', () => {
      const key = 'A'.repeat(40)

      expect(sanitizeForLogging(key)).toBe(key)
    })

    it('keeps redacting later strings after an earlier match (no stateful regex)', () => {
      expect(sanitizeForLogging('first user@example.com')).toBe('first [REDACTED_EMAIL]')
      expect(sanitizeForLogging('x.y and c.123A>G')).toBe('x.y and [REDACTED_VARIANT]')
    })
  })

  describe('sanitizeLogEntry', () => {
    it('sanitises both message and data', () => {
      expect(sanitizeLogEntry('login user@example.com', { password: 'x' })).toEqual({
        message: 'login [REDACTED_EMAIL]',
        data: { password: '[REDACTED_SENSITIVE]' }
      })
    })

    it('uses an empty message and null data when both are missing', () => {
      expect(sanitizeLogEntry(null)).toEqual({ message: '', data: null })
      expect(sanitizeLogEntry(undefined, undefined)).toEqual({ message: '', data: null })
    })
  })

  describe('containsSensitiveData', () => {
    it('detects common sensitive keywords in strings and objects', () => {
      expect(containsSensitiveData('my password is set')).toBe(true)
      expect(containsSensitiveData({ token: 'x' })).toBe(true)
      expect(containsSensitiveData({ hgvs: 'c.1A>G' })).toBe(true)
    })

    it('returns false for empty or clean values', () => {
      expect(containsSensitiveData(null)).toBe(false)
      expect(containsSensitiveData('')).toBe(false)
      expect(containsSensitiveData({ name: 'John' })).toBe(false)
    })
  })

  it('testSanitization reports success for its built-in cases', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(testSanitization()).toBe(true)
    expect(errorSpy).not.toHaveBeenCalled()
  })
})
