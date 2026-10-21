import { describe, it, expect, vi, afterEach } from 'vitest'
import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useTableUrlState } from '../useTableUrlState'

async function setup(
  url = '/t',
  opts: Parameters<typeof useTableUrlState>[0] = { filterKeys: ['status', 'scope'] },
  count = 1
) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/t', component: { template: '<div/>' } }]
  })
  await router.push(url)
  const apis: ReturnType<typeof useTableUrlState>[] = []
  const app = createApp({
    setup() {
      for (let i = 0; i < count; i++) apis.push(useTableUrlState(i === 0 ? opts : { prefix: 'b' }))
      return () => null
    }
  })
  app.use(router).mount(document.createElement('div'))
  return { router, api: apis[0]!, apis }
}

describe('useTableUrlState', () => {
  it('reads state from the URL', async () => {
    const { api } = await setup(
      '/t?q=pkd&page=3&size=50&sort=symbol&order=desc&density=compact&status=active'
    )
    expect(api.search.value).toBe('pkd')
    expect(api.page.value).toBe(3)
    expect(api.itemsPerPage.value).toBe(50)
    expect(api.sortBy.value).toEqual([{ key: 'symbol', order: 'desc' }])
    expect(api.density.value).toBe('compact')
    expect(api.filters.value).toEqual({ status: 'active' })
  })

  it('falls back to defaults and ignores junk', async () => {
    const { api } = await setup('/t?page=abc&size=-4&other=1')
    expect(api.page.value).toBe(1)
    expect(api.itemsPerPage.value).toBe(25)
    expect(api.sortBy.value).toEqual([])
    expect(api.density.value).toBe('comfortable')
    expect(api.filters.value).toEqual({})
  })

  it('writes changes to the URL, omits defaults and resets the page', async () => {
    const { api, router } = await setup('/t?page=4')
    api.search.value = 'abc'
    await new Promise(r => setTimeout(r, 350))
    expect(router.currentRoute.value.query).toEqual({ q: 'abc' })
    api.page.value = 2
    api.filters.value = { status: 'active', scope: '' }
    await new Promise(r => setTimeout(r))
    expect(router.currentRoute.value.query).toEqual({ q: 'abc', status: 'active' })
    api.sortBy.value = [{ key: 'symbol', order: 'asc' }]
    api.density.value = 'compact'
    api.itemsPerPage.value = 10
    await new Promise(r => setTimeout(r))
    expect(router.currentRoute.value.query).toEqual({
      q: 'abc',
      status: 'active',
      sort: 'symbol',
      order: 'asc',
      density: 'compact',
      size: '10'
    })
    api.sortBy.value = []
    api.search.value = ''
    await new Promise(r => setTimeout(r, 350))
    expect(router.currentRoute.value.query.sort).toBeUndefined()
    expect(router.currentRoute.value.query.q).toBeUndefined()
  })

  it('debounces the search write', async () => {
    vi.useFakeTimers()
    const { api, router } = await setup()
    api.search.value = 'a'
    api.search.value = 'ab'
    expect(api.search.value).toBe('ab')
    await vi.advanceTimersByTimeAsync(299)
    expect(router.currentRoute.value.query.q).toBeUndefined()
    await vi.advanceTimersByTimeAsync(10)
    expect(router.currentRoute.value.query.q).toBe('ab')
  })

  it('clamps size to the offered options and page to a safe integer', async () => {
    for (const url of [
      '/t?size=100000&page=1e20',
      '/t?size=7&page=0',
      '/t?size=%F0%9F%90%88&page=%E2%80%AE',
      '/t?size=25.5&page=-3'
    ]) {
      const { api } = await setup(url)
      expect(api.itemsPerPage.value).toBe(25)
      expect(api.page.value).toBe(1)
    }
    expect((await setup('/t?size=100')).api.itemsPerPage.value).toBe(100)
  })

  it('rejects filter keys that clash with reserved keys', async () => {
    await expect(setup('/t', { filterKeys: ['page'] })).rejects.toThrow(/reserved/)
  })

  it('keeps two prefixed instances on one route apart', async () => {
    const { apis, router } = await setup('/t', { prefix: 'a', filterKeys: ['status'] }, 2)
    apis[0]!.page.value = 3
    apis[1]!.page.value = 2
    apis[0]!.filters.value = { status: 'x' }
    await new Promise(r => setTimeout(r))
    expect(router.currentRoute.value.query).toEqual({ 'a.status': 'x', 'b.page': '2' })
    apis[1]!.sortBy.value = [{ key: 'k', order: 'desc' }]
    await new Promise(r => setTimeout(r))
    expect(router.currentRoute.value.query).toMatchObject({ 'a.status': 'x', 'b.sort': 'k' })
    expect(apis[0]!.page.value).toBe(1)
  })

  it('reads and writes multi-select filters as repeated keys', async () => {
    const { api, router } = await setup('/t?cls=a&cls=b', {
      filterKeys: ['cls'],
      multiKeys: ['cls']
    })
    expect(api.filters.value).toEqual({ cls: ['a', 'b'] })
    api.filters.value = { cls: ['c'] }
    await new Promise(r => setTimeout(r))
    expect(router.currentRoute.value.query.cls).toEqual(['c'])
  })

  afterEach(() => vi.useRealTimers())
})
