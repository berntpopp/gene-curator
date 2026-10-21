import { describe, it, expect } from 'vitest'
import { hasContent } from '../hasContent'

describe('hasContent', () => {
  it('ignores blank rows added but never filled in', () => {
    expect(hasContent([])).toBe(false)
    expect(hasContent([{}])).toBe(false)
    expect(hasContent([{ pmid: '', note: '  ', tags: [], x: null }])).toBe(false)
    expect(hasContent(undefined)).toBe(false)
  })

  it('ignores the defaults a freshly added contradictory row comes with', () => {
    const fresh = {
      label: '',
      pmid: '',
      evidence_type: 'population',
      description: '',
      impact: 'note',
      explanation: ''
    }
    expect(hasContent([fresh])).toBe(false)
    expect(hasContent([{ ...fresh, impact: 'disputed' }])).toBe(true)
    expect(hasContent([{ ...fresh, description: 'x' }])).toBe(true)
  })

  it('counts a row with any entered value', () => {
    expect(hasContent([{ pmid: '' }, { pmid: '123' }])).toBe(true)
    expect(hasContent([{ points: 0 }])).toBe(true)
    expect(hasContent([{ flag: true }])).toBe(true)
  })
})
