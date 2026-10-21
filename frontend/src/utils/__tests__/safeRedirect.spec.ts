import { describe, it, expect } from 'vitest'
import { safeRedirect } from '../safeRedirect'

describe('safeRedirect', () => {
  it.each(['/genes', '/faq?x=1#a', '/scopes/abc/genes'])('accepts %s', p => {
    expect(safeRedirect(p)).toBe(p)
  })

  it.each([
    '//evil.example',
    '/\\evil.example',
    'https://evil.example',
    'javascript:alert(1)',
    '%2F%2Fevil.example',
    '/%2Fevil.example',
    '/%5Cevil.example',
    '/%252F',
    '/%',
    '/\t/evil.example',
    'genes',
    '',
    undefined,
    null,
    ['/genes']
  ])('rejects %j', p => {
    expect(safeRedirect(p)).toBeUndefined()
  })
})
