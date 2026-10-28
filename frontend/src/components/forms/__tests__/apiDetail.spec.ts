import { describe, it, expect } from 'vitest'
import { apiDetail } from '../apiDetail'

const fail = (detail: unknown) => ({ response: { data: { detail } } })

describe('apiDetail', () => {
  it('names the rows and fields a refused submit lists', () => {
    const detail = {
      message: 'Evidence has invalid values; fix these fields and resubmit',
      errors: [
        { path: 'genetic_evidence.segregation[1].variant', message: 'Scored row needs a variant' },
        { path: 'disease', message: 'Required' }
      ]
    }
    expect(apiDetail(fail(detail), 'x')).toBe(
      'Evidence has invalid values; fix these fields and resubmit: ' +
        'Genetic evidence › segregation #2 › Variant: Scored row needs a variant; Disease: Required'
    )
  })

  it('keeps the plain message, string and first-msg forms', () => {
    expect(apiDetail(fail({ message: 'Nope' }), 'x')).toBe('Nope')
    expect(apiDetail(fail('Gone'), 'x')).toBe('Gone')
    expect(apiDetail(fail([{ msg: 'Bad' }]), 'x')).toBe('Bad')
    expect(apiDetail(null, 'fallback')).toBe('fallback')
  })
})
