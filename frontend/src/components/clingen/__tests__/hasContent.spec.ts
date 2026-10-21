import { describe, it, expect } from 'vitest'
import { hasContent } from '../hasContent'

describe('hasContent', () => {
  it('ignores blank rows added but never filled in', () => {
    expect(hasContent([])).toBe(false)
    expect(hasContent([{}])).toBe(false)
    expect(hasContent([{ pmid: '', note: '  ', tags: [], x: null }])).toBe(false)
    expect(hasContent(undefined)).toBe(false)
  })

  it('counts a row with any entered value', () => {
    expect(hasContent([{ pmid: '' }, { pmid: '123' }])).toBe(true)
    expect(hasContent([{ points: 0 }])).toBe(true)
    expect(hasContent([{ flag: true }])).toBe(true)
  })
})
