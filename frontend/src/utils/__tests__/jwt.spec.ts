import { describe, it, expect } from 'vitest'
import { getTokenExpiry } from '../jwt'

const token = (payload: object): string => `h.${btoa(JSON.stringify(payload))}.s`

describe('getTokenExpiry', () => {
  it('returns exp in milliseconds', () => {
    expect(getTokenExpiry(token({ exp: 1000 }))).toBe(1_000_000)
  })

  it('decodes base64url payloads', () => {
    const b64url = btoa(JSON.stringify({ exp: 5, x: '??>>' }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')
    expect(getTokenExpiry(`h.${b64url}.s`)).toBe(5000)
  })

  it('returns null for missing exp, garbage and non-JWT strings', () => {
    expect(getTokenExpiry(token({}))).toBeNull()
    expect(getTokenExpiry(token({ exp: 'soon' }))).toBeNull()
    expect(getTokenExpiry('h.!!!.s')).toBeNull()
    expect(getTokenExpiry('opaque')).toBeNull()
  })
})
