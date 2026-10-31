import { describe, it, expect, vi, beforeEach } from 'vitest'

const get = vi.hoisted(() => vi.fn())
const put = vi.hoisted(() => vi.fn())
vi.mock('../client', () => ({ default: { get, put } }))

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

  it('lists the classes the catalogue can filter by', async () => {
    get.mockResolvedValue({ data: ['strong'] })
    expect(await catalogueMatrixAPI.getClassifications()).toEqual(['strong'])
    expect(get).toHaveBeenCalledWith('/gene-catalogue/filters/classifications')
  })

  it("reads and saves the user's catalogue view (#276)", async () => {
    get.mockResolvedValue({ data: { scope_ids: ['b', 'a'] } })
    expect(await catalogueMatrixAPI.getSavedView()).toEqual(['b', 'a'])
    expect(get).toHaveBeenCalledWith('/me/views/catalogue')
    get.mockResolvedValue({ data: {} })
    expect(await catalogueMatrixAPI.getSavedView()).toEqual([])
    put.mockResolvedValue({ data: {} })
    await catalogueMatrixAPI.saveView(['a'])
    expect(put).toHaveBeenCalledWith('/me/views/catalogue', { scope_ids: ['a'] })
  })
})
