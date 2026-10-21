import { describe, it, expect } from 'vitest'
import { readableApiError } from '../apiErrorText'

const err = (detail: unknown, message?: string) => ({ message, response: { data: { detail } } })

describe('readableApiError', () => {
  it('returns a string detail as is', () => {
    expect(readableApiError(err('Curation is not in draft'), 'x')).toBe('Curation is not in draft')
  })

  it('turns a 422 detail array into one readable sentence, never JSON', () => {
    const detail = [
      {
        type: 'string_too_long',
        loc: ['body', 'notes'],
        msg: 'String should have at most 2000 characters',
        input: 'xxx',
        ctx: { max_length: 2000 }
      },
      { type: 'missing', loc: ['body', 'target_stage'], msg: 'Field required' }
    ]
    const text = readableApiError(err(detail), 'x')
    expect(text).toBe(
      'Notes: String should have at most 2000 characters. Target stage: Field required.'
    )
    expect(text).not.toContain('{')
    expect(text).not.toContain('loc')
  })

  it('handles array entries without a location or message', () => {
    expect(readableApiError(err([{ msg: 'Value error, bad' }]), 'x')).toBe('Value error, bad.')
    expect(readableApiError(err([{ loc: ['body', 'a'] }, 7]), 'fallback')).toBe('fallback')
  })

  it('reads an object detail with a message', () => {
    expect(readableApiError(err({ message: 'Conflict' }), 'x')).toBe('Conflict')
  })

  it('falls back to the error message, then the fallback', () => {
    expect(readableApiError({ message: 'Network Error' }, 'x')).toBe('Network Error')
    expect(readableApiError(null, 'Request failed')).toBe('Request failed')
    expect(readableApiError(err({}), 'Request failed')).toBe('Request failed')
  })
})
