import { describe, it, expect, vi, beforeEach } from 'vitest'

const get = vi.hoisted(() => vi.fn())
vi.mock('../client', () => ({ default: { get } }))

import { catalogueMatrixAPI } from '../catalogueMatrix'

describe('catalogueMatrixAPI', () => {
  beforeEach(() => get.mockReset())

  it('requests the matrix and serialises scope_ids as repeated keys', async () => {
    get.mockResolvedValue({ data: { rows: [] } })
    await catalogueMatrixAPI.getMatrix({ scope_ids: ['a', 'b'], search: 'pkd', limit: 25 })
    const [url, config] = get.mock.calls[0]!
    expect(url).toBe('/gene-catalogue/matrix')
    expect(config.params.scope_ids).toEqual(['a', 'b'])
    expect(config.paramsSerializer).toEqual({ indexes: null })
  })

  it('lists scopes that have curations', async () => {
    get.mockResolvedValue({ data: [{ id: 's1' }] })
    expect(await catalogueMatrixAPI.getScopes()).toEqual([{ id: 's1' }])
    expect(get).toHaveBeenCalledWith('/gene-catalogue/filters/scopes')
  })
})
