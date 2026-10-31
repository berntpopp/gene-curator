import { describe, it, expect, vi } from 'vitest'
import apiClient from '../client'
import { moveToVersion } from '../methodologyImport'

vi.mock('../client', () => ({ default: { post: vi.fn() } }))

describe('moveToVersion', () => {
  it('posts the dry run flag and target version', async () => {
    vi.mocked(apiClient).post.mockResolvedValue({ data: { items: [] } })
    await expect(moveToVersion('s', false, 2)).resolves.toEqual({ items: [] })
    expect(apiClient.post).toHaveBeenCalledWith(
      '/schemas/curation-schemas/s/move-to-version',
      null,
      { params: { dry_run: false, version: 2 } }
    )
  })
})
