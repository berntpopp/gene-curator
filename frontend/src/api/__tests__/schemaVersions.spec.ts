import { describe, it, expect, vi } from 'vitest'
import apiClient from '../client'
import { schemasAPI } from '../schemas'

vi.mock('../client', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

const client = vi.mocked(apiClient)

describe('schemasAPI methodology versions', () => {
  it('lists versions and derives from one', async () => {
    client.get.mockResolvedValue({ data: ['v'] })
    client.post.mockResolvedValue({ data: { id: 'new' } })

    await expect(schemasAPI.getVersions('s')).resolves.toEqual(['v'])
    expect(client.get).toHaveBeenCalledWith('/schemas/curation-schemas/s/versions')

    const body = { name: 'n', version: '1' }
    await expect(schemasAPI.deriveSchema('s', 'v1', body)).resolves.toEqual({ id: 'new' })
    expect(client.post).toHaveBeenCalledWith('/schemas/curation-schemas/s/versions/v1/derive', body)
  })

  it('reads one methodology version', async () => {
    client.get.mockResolvedValue({ data: { id: 'v1' } })
    await expect(schemasAPI.getMethodologyVersion('v1')).resolves.toEqual({ id: 'v1' })
    expect(client.get).toHaveBeenCalledWith('/schemas/methodology-versions/v1')
  })
})
