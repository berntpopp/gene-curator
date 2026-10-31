import { describe, it, expect } from 'vitest'
import { noActionsReason } from '../noActionsReason'

describe('noActionsReason', () => {
  it('names the correction only while the curation is in review', () => {
    expect(noActionsReason({ status: 'in_review', corrected_disease: true }, false)).toContain(
      'You corrected the disease entity'
    )
    expect(noActionsReason({ status: 'active', corrected_disease: true }, false)).toBe(
      'No actions available'
    )
  })

  it('counts one approval in the singular', () => {
    expect(noActionsReason({ status: 'in_review', approvals_remaining: 1 }, false)).toBe(
      'Waiting for 1 more approval'
    )
  })
})
