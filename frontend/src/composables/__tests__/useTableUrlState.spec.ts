import { describe, it, expect } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useTableUrlState } from '../useTableUrlState'

async function setup(url = '/t') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/t', component: { template: '<div/>' } }]
  })
  await router.push(url)
  const state = router.currentRoute.value
  void state
  let api!: ReturnType<typeof useTableUrlState>
  const app = (await import('vue')).createApp({
    setup() {
      api = useTableUrlState({ filterKeys: ['status', 'scope'] })
      return () => null
    }
  })
  app.use(router).mount(document.createElement('div'))
  return { router, api }
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
    await router.isReady()
    await new Promise(r => setTimeout(r))
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
    await new Promise(r => setTimeout(r))
    expect(router.currentRoute.value.query.sort).toBeUndefined()
    expect(router.currentRoute.value.query.q).toBeUndefined()
  })
})
