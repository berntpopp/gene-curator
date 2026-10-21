import { describe, it, expect, vi, beforeEach } from 'vitest'

const post = vi.hoisted(() => vi.fn())
vi.mock('../client', () => ({ default: { post } }))

import { publicationsAPI } from '../publications'

describe('publicationsAPI.validatePMIDs', () => {
  beforeEach(() => post.mockReset().mockResolvedValue({ data: { results: [] } }))

  it('posts the PMIDs, unchanged when there is no signal', async () => {
    await publicationsAPI.validatePMIDs(['1'])
    expect(post).toHaveBeenCalledWith('/publications/validate', { pmids: ['1'] })
  })

  it('passes an abort signal through so a lookup can be cancelled', async () => {
    const { signal } = new AbortController()
    await publicationsAPI.validatePMIDs(['1'], signal)
    expect(post).toHaveBeenCalledWith('/publications/validate', { pmids: ['1'] }, { signal })
  })
})
