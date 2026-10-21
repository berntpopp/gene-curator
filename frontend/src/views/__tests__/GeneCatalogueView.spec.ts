import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

const api = vi.hoisted(() => ({ getMatrix: vi.fn(), getScopes: vi.fn() }))
vi.mock('@/api/catalogueMatrix', () => ({ catalogueMatrixAPI: api }))
const scopesApi = vi.hoisted(() => ({ fetchUserScopes: vi.fn() }))
vi.mock('@/stores/scopes', () => ({
  useScopesStore: () => ({ userScopes: [], fetchUserScopes: scopesApi.fetchUserScopes })
}))

import { useAuthStore } from '@/stores/auth'
import GeneCatalogueView from '../GeneCatalogueView.vue'

const scopes = [
  { id: 's1', name: 'kidney', display_name: 'Kidney genetics', is_public: true },
  { id: 's2', name: 'cilia', display_name: 'Ciliopathies', is_public: true }
]
const cell = (scope: string, over: Record<string, unknown> = {}) => ({
  scope_id: scope,
  curation_id: `c-${scope}`,
  classification: 'Definitive',
  stage: 'active',
  status: 'active',
  total_score: 14.5,
  in_progress: false,
  ...over
})
const row = (symbol: string, agreement: string, cells: unknown[]) => ({
  gene_id: `g-${symbol}`,
  hgnc_id: 'HGNC:1',
  approved_symbol: symbol,
  agreement,
  cells
})
const response = {
  scopes,
  total: 87,
  skip: 0,
  limit: 25,
  has_next: true,
  has_prev: false,
  rows: [
    row('PKD1', 'disagree', [cell('s1'), cell('s2', { classification: 'Disputed' })]),
    row('NAA10', 'single', [cell('s1', { classification: null, total_score: null })]),
    row('HNF1B', 'agree', [
      cell('s1', { in_progress: true, status: 'in_review', stage: 'review', classification: null })
    ])
  ]
}

async function mountView(url = '/genes') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/genes', component: GeneCatalogueView },
      { path: '/genes/:id', component: { template: '<div/>' } },
      { path: '/scopes/:scopeId/curations/:curationId', component: { template: '<div/>' } }
    ]
  })
  await router.push(url)
  const wrapper = mount(GeneCatalogueView, {
    global: { plugins: [router] },
    attachTo: document.body
  })
  await flushPromises()
  await new Promise(r => setTimeout(r))
  await flushPromises()
  return { wrapper, router }
}

describe('GeneCatalogueView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    api.getScopes.mockReset().mockResolvedValue(scopes)
    api.getMatrix.mockReset().mockResolvedValue(response)
    scopesApi.fetchUserScopes.mockReset().mockResolvedValue([])
  })

  it('fetches the default scopes and shows the server total', async () => {
    const { wrapper } = await mountView()
    expect(api.getMatrix.mock.calls[0]![0]).toMatchObject({
      scope_ids: ['s1', 's2'],
      skip: 0,
      limit: 25
    })
    expect(wrapper.text()).toContain('1-25 of 87')
    expect(wrapper.find('[data-testid="scope-picker"]').text()).toBe('Scopes shown: 2 of 2')
  })

  it('renders one column per scope with classification marks and honest empty cells', async () => {
    const { wrapper } = await mountView()
    const heads = wrapper.findAll('thead th').map(h => h.text())
    expect(heads).toEqual(['Gene', 'Kidney genetics', 'Ciliopathies', 'Agreement'])
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0]!.text()).toContain('Definitive')
    expect(rows[0]!.text()).toContain('Disputed')
    expect(rows[0]!.text()).toContain('14.5')
    expect(rows[1]!.text()).toContain('Not classified')
    expect(rows[1]!.text()).not.toContain('Pending')
    expect(rows[1]!.text()).toContain('not in scope')
    expect(rows[2]!.text()).toContain('In review')
  })

  it('keeps scores neutral and drops the old quick-view, tiles and per-row icons', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.find('.text-success').exists()).toBe(false)
    expect(wrapper.find('.v-avatar').exists()).toBe(false)
    expect(wrapper.find('.mdi-virus').exists()).toBe(false)
    expect(wrapper.find('[data-testid="quick-view"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Curated Genes')
  })

  it('names every cell link and marks disagreeing rows', async () => {
    const { wrapper } = await mountView()
    const link = wrapper.find('tbody tr a[href*="/scopes/s1/curations/c-s1"]')
    expect(link.attributes('aria-label')).toBe('Open PKD1 curation in Kidney genetics')
    expect(wrapper.findAll('a').every(a => a.text() || a.attributes('aria-label'))).toBe(true)
    expect(wrapper.findAll('.agreement--disagree')).toHaveLength(1)
    expect(wrapper.find('.agreement--disagree').text()).toBe('Disagree')
  })

  it('restores filters and scopes from the URL', async () => {
    const { wrapper } = await mountView('/genes?agreement=disagree&scopes=s2&q=pkd&page=2&size=50')
    expect(api.getMatrix.mock.calls.at(-1)![0]).toMatchObject({
      scope_ids: ['s2'],
      agreement: 'disagree',
      search: 'pkd',
      skip: 50,
      limit: 50
    })
    expect(wrapper.find('[data-testid="filter-agreement"]').text()).toContain('Disagree')
  })

  it('uses the saved default view when the URL names no scopes', async () => {
    localStorage.setItem('catalogue.shownScopes', JSON.stringify(['s2']))
    await mountView()
    expect(api.getMatrix.mock.calls[0]![0].scope_ids).toEqual(['s2'])
  })

  it('writes a scope change to the URL and saves it as the default', async () => {
    const { wrapper, router } = await mountView()
    await wrapper.find('[data-testid="scope-picker"]').trigger('click')
    await new Promise(r => setTimeout(r, 50))
    ;(document.body.querySelector('[data-testid="scope-s2"] input') as HTMLInputElement).click()
    await new Promise(r => setTimeout(r, 20))
    await flushPromises()
    expect(router.currentRoute.value.query.scopes).toEqual(['s1'])
    expect(JSON.parse(localStorage.getItem('catalogue.shownScopes')!)).toEqual(['s1'])
    expect(api.getMatrix.mock.calls.at(-1)![0].scope_ids).toEqual(['s1'])
  })

  it('shows the error with retry, not the empty state', async () => {
    api.getMatrix.mockRejectedValue({ response: { data: { detail: 'Server down' } } })
    const { wrapper } = await mountView()
    expect(wrapper.find('[data-testid="table-error"]').text()).toContain('Server down')
    expect(wrapper.find('[data-testid="table-empty"]').exists()).toBe(false)
    api.getMatrix.mockResolvedValue(response)
    await wrapper.find('[data-testid="table-retry"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="table-error"]').exists()).toBe(false)
  })

  it('loads the signed-in user scopes once authentication settles, not only at mount', async () => {
    await mountView()
    expect(scopesApi.fetchUserScopes).not.toHaveBeenCalled()
    useAuthStore().isAuthenticated = true
    await flushPromises()
    expect(scopesApi.fetchUserScopes).toHaveBeenCalledTimes(1)
  })
})
