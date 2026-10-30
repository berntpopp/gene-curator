import { describe, it, expect } from 'vitest'
import { blockedBy } from '../approvalNotice'

describe('blockedBy', () => {
  it('names the blocking curation by its gene, not its UUID (#530)', () => {
    const id = '0b6f1c8e-1f2a-4c3d-9e8f-123456789abc'
    const notice = blockedBy({
      precuration_id: 'p1',
      approved: true,
      curation_created: false,
      curation_id: id,
      message: `Precuration approved; no curation created: Open curation ${id} has no disease entity`
    })
    expect(notice).toEqual({
      curationId: id,
      message:
        'Precuration approved; no curation created: Open curation of this gene has no disease entity'
    })
  })

  it('is null when the approval created a curation', () => {
    const r = { precuration_id: 'p1', approved: true, curation_created: true, curation_id: 'c1' }
    expect(blockedBy({ ...r, message: 'ok' })).toBeNull()
  })
})
