/**
 * Tests for errorDetails (log payload for caught values).
 *
 * @see src/components/dynamic/errorDetails.ts
 */

import { describe, it, expect } from 'vitest'
import { errorDetails } from '../errorDetails'

describe('errorDetails', () => {
  it('returns message and stack for Error instances', () => {
    const error = new Error('boom')
    const details = errorDetails(error)

    expect(details.error).toBe('boom')
    expect(details.stack).toBe(error.stack)
  })

  it('stringifies non-Error values without a stack', () => {
    expect(errorDetails('plain failure')).toEqual({ error: 'plain failure' })
    expect(errorDetails(42)).toEqual({ error: '42' })
  })
})
