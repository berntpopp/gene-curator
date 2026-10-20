import { describe, it, expect } from 'vitest'
import type { CurationStatus } from '../status'
import { CURATION_STATUS, curationStatusColor, curationStatusLabel } from '../status'

// Typed list: vue-tsc fails if the backend enum gains or loses a value that this list does not match.
const ALL_STATUSES: CurationStatus[] = [
  'draft',
  'submitted',
  'in_review',
  'approved',
  'rejected',
  'active',
  'archived'
]

describe('curation status config', () => {
  it.each(ALL_STATUSES)('has a label and colour for %s', status => {
    expect(CURATION_STATUS[status].label).toBeTruthy()
    expect(CURATION_STATUS[status].color).toBeTruthy()
  })

  it('labels in_review as "In review"', () => {
    expect(curationStatusLabel('in_review')).toBe('In review')
    expect(curationStatusColor('in_review')).toBe('warning')
  })

  it('falls back for unknown or empty values', () => {
    expect(curationStatusLabel('no_such_status')).toBe('no_such_status')
    expect(curationStatusColor('no_such_status')).toBe('grey')
    expect(curationStatusLabel(null)).toBe('Unknown')
    expect(curationStatusColor(undefined)).toBe('grey')
  })
})
