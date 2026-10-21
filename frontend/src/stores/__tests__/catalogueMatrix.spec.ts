import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const api = vi.hoisted(() => ({ getMatrix: vi.fn(), getScopes: vi.fn() }))
vi.mock('@/api/catalogueMatrix', () => ({ catalogueMatrixAPI: api }))

import { useCatalogueMatrixStore } from '../catalogueMatrix'

const scopes = ['a', 'b', 'c'].map(id => ({ id, name: id, display_name: id.toUpperCase() }))
const KEY = 'catalogue.shownScopes'

describe('catalogueMatrix store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api.getMatrix.mockReset()
    api.getScopes.mockReset()
    localStorage.clear()
  })

  it('shows the first scopes by default and remembers the choice', async () => {
    api.getScopes.mockResolvedValue(scopes)
    const store = useCatalogueMatrixStore()
    await store.loadScopes()
    expect(store.availableScopes).toHaveLength(3)
    expect(store.defaultShownIds).toEqual(['a', 'b', 'c'])
    store.saveDefault(['c', 'a'])
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual(['c', 'a'])
    expect(store.defaultShownIds).toEqual(['c', 'a'])
  })

  it('drops saved scopes that are no longer available and survives bad storage', async () => {
    api.getScopes.mockResolvedValue(scopes)
    localStorage.setItem(KEY, JSON.stringify(['gone', 'b']))
    const store = useCatalogueMatrixStore()
    await store.loadScopes()
    expect(store.defaultShownIds).toEqual(['b'])
    localStorage.setItem(KEY, '{not json')
    setActivePinia(createPinia())
    const again = useCatalogueMatrixStore()
    await again.loadScopes()
    expect(again.defaultShownIds).toEqual(['a', 'b', 'c'])
  })

  it('works when localStorage throws', async () => {
    api.getScopes.mockResolvedValue(scopes)
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const store = useCatalogueMatrixStore()
    await store.loadScopes()
    expect(() => store.saveDefault(['a'])).not.toThrow()
    expect(store.defaultShownIds).toEqual(['a'])
    spy.mockRestore()
    set.mockRestore()
  })

  it('fetches the matrix with server paging params and keeps server totals', async () => {
    api.getMatrix.mockResolvedValue({ scopes: [scopes[0]], rows: [{ gene_id: 'g' }], total: 120 })
    const store = useCatalogueMatrixStore()
    await store.fetch({
      scopeIds: ['a'],
      search: 'x',
      agreement: 'disagree',
      page: 3,
      size: 25,
      desc: true
    })
    expect(api.getMatrix).toHaveBeenCalledWith({
      scope_ids: ['a'],
      search: 'x',
      agreement: 'disagree',
      skip: 50,
      limit: 25,
      sort_order: 'desc'
    })
    expect(store.total).toBe(120)
    expect(store.rows).toHaveLength(1)
    expect(store.error).toBeNull()
  })

  it('skips the request with no scopes and reports errors', async () => {
    const store = useCatalogueMatrixStore()
    await store.fetch({ scopeIds: [], page: 1, size: 25 })
    expect(api.getMatrix).not.toHaveBeenCalled()
    expect(store.rows).toEqual([])
    api.getMatrix.mockRejectedValue({ response: { data: { detail: 'boom' } } })
    await store.fetch({ scopeIds: ['a'], page: 1, size: 25 })
    expect(store.error).toBe('boom')
    expect(store.rows).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('reports a failed scope list', async () => {
    api.getScopes.mockRejectedValue(new Error('down'))
    const store = useCatalogueMatrixStore()
    await store.loadScopes()
    expect(store.error).toBe('down')
  })
})
