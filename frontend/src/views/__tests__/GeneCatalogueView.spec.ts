import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

const api = vi.hoisted(() => ({
  getMatrix: vi.fn(),
  getScopes: vi.fn(),
  getClassifications: vi.fn(),
  getSavedView: vi.fn(),
  saveView: vi.fn()
}))
vi.mock('@/api/catalogueMatrix', () => ({ catalogueMatrixAPI: api }))
const scopesApi = vi.hoisted(() => ({ fetchUserScopes: vi.fn() }))
const userScopes = vi.hoisted(() => ({
  list: [] as { id: string; display_name: string; user_role?: string }[]
}))
vi.mock('@/stores/scopes', () => ({
  useScopesStore: () => ({
    get userScopes() {
      return userScopes.list
    },
    fetchUserScopes: scopesApi.fetchUserScopes
  })
}))

import { useAuthStore } from '@/stores/auth'
import { useCatalogueMatrixStore } from '@/stores/catalogueMatrix'
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

const mounted: { unmount: () => void }[] = []

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
  mounted.push(wrapper)
  return { wrapper, router }
}

describe('GeneCatalogueView', () => {
  // Unmount so teleported menus from earlier tests cannot be hit by document.body queries.
  afterEach(() => mounted.splice(0).forEach(w => w.unmount()))

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    api.getScopes.mockReset().mockResolvedValue(scopes)
    api.getMatrix.mockReset().mockResolvedValue(response)
    api.getClassifications.mockReset().mockResolvedValue(['limited', 'definitive'])
    api.getSavedView.mockReset().mockResolvedValue([])
    api.saveView.mockReset().mockResolvedValue(undefined)
    userScopes.list = []
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
    expect(rows[1]!.text()).toContain('no active curation')
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

  it('shows a susceptibility curation next to the mendelian one in a scope (#539)', async () => {
    api.getMatrix.mockResolvedValue({
      ...response,
      rows: [
        row('WT1', 'single', [
          cell('s1', { classification: 'Limited', total_score: null }),
          cell('s1', {
            curation_id: 'c-sus',
            relationship_type: 'susceptibility',
            classification: 'Strong',
            total_score: null
          })
        ])
      ]
    })
    const { wrapper } = await mountView()
    const first = wrapper.findAll('tbody tr')[0]!
    expect(first.findAll('a.cell-link')).toHaveLength(2)
    expect(first.text()).toContain('Limited')
    expect(first.text()).toMatch(/Strong.*\(Susceptibility\)/)
    expect(first.find('a[href*="c-sus"]').attributes('aria-label')).toBe(
      'Strong (Susceptibility), open WT1 curation in Kidney genetics'
    )
  })

  it("labels a scope's custom class from its declared vocabulary (#539)", async () => {
    const vocab = [
      { key: 'kidney_candidate', label: 'Kidney candidate', order: 1, tone: 'moderate' }
    ]
    api.getMatrix.mockResolvedValue({
      ...response,
      scopes: [{ ...scopes[0], classifications: vocab }, scopes[1]],
      rows: [row('PKD1', 'single', [cell('s1', { classification: 'kidney_candidate' })])]
    })
    const { wrapper } = await mountView()
    const first = wrapper.findAll('tbody tr')[0]!
    expect(first.text()).toContain('Kidney candidate')
    expect(first.text()).not.toContain('kidney_candidate')
  })

  it('names every cell link and marks disagreeing rows', async () => {
    const { wrapper } = await mountView()
    const link = wrapper.find('tbody tr a[href*="/scopes/s1/curations/c-s1"]')
    expect(link.attributes('aria-label')).toBe(
      'Definitive 14.5, open PKD1 curation in Kidney genetics'
    )
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

  it('toggles the Disagreements chip beside the table (Wave 10 polish)', async () => {
    const { wrapper, router } = await mountView()
    const chip = () => wrapper.find('[data-testid="disagreements-chip"]')
    expect(chip().attributes('aria-pressed')).toBe('false')
    await chip().trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query.agreement).toBe('disagree'))
    expect(api.getMatrix.mock.calls.at(-1)![0]).toMatchObject({ agreement: 'disagree' })
    expect(chip().attributes('aria-pressed')).toBe('true')
    await chip().trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query.agreement).toBeUndefined())
    await flushPromises()
    expect(api.getMatrix.mock.calls.at(-1)![0].agreement).toBeUndefined()
  })

  it('filters by a classification the catalogue has, strongest first (#539)', async () => {
    const { wrapper } = await mountView('/genes?classification=definitive')
    expect(api.getMatrix.mock.calls.at(-1)![0]).toMatchObject({ classification: 'definitive' })
    expect(wrapper.find('[data-testid="filter-classification"]').text()).toContain('Definitive')
    const store = useCatalogueMatrixStore()
    expect(store.classifications).toEqual(['limited', 'definitive'])
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
    await vi.waitFor(() => expect(router.currentRoute.value.query.scopes).toEqual(['s1']))
    expect(JSON.parse(localStorage.getItem('catalogue.shownScopes')!)).toEqual(['s1'])
    expect(api.getMatrix.mock.calls.at(-1)![0].scope_ids).toEqual(['s1'])
  })

  it('applies the Disagreements preset as the agreement filter (#276)', async () => {
    const { wrapper, router } = await mountView()
    await wrapper.find('[data-testid="scope-picker"]').trigger('click')
    await new Promise(r => setTimeout(r, 50))
    ;(document.body.querySelector('[data-testid="preset-disagreements"]') as HTMLElement).click()
    await vi.waitFor(() => expect(router.currentRoute.value.query.agreement).toBe('disagree'))
    expect(api.getMatrix.mock.calls.at(-1)![0]).toMatchObject({ agreement: 'disagree' })
    expect(wrapper.find('[data-testid="filter-agreement"]').text()).toContain('Disagree')
  })

  it('keeps the gene column sticky while scope columns scroll (#276)', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.find('th.v-data-table-column--fixed').exists()).toBe(true)
    expect(wrapper.findAll('td.v-data-table-column--fixed')).toHaveLength(3)
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

  it("restores the signed-in user's saved column order from the server (#276)", async () => {
    api.getSavedView.mockResolvedValue(['s2', 's1'])
    await mountView()
    useAuthStore().isAuthenticated = true
    await vi.waitFor(() =>
      expect(api.getMatrix.mock.calls.at(-1)![0].scope_ids).toEqual(['s2', 's1'])
    )
  })

  it('saves a signed-in scope change on the server, an anonymous one only locally (#276)', async () => {
    const { wrapper } = await mountView()
    const pick = async (id: string) => {
      await wrapper.find('[data-testid="scope-picker"]').trigger('click')
      await new Promise(r => setTimeout(r, 50))
      ;(
        document.body.querySelector(`[data-testid="scope-${id}"] input`) as HTMLInputElement
      ).click()
      await flushPromises()
    }
    await pick('s2')
    expect(api.saveView).not.toHaveBeenCalled()
    useAuthStore().isAuthenticated = true
    await flushPromises()
    await pick('s2')
    expect(api.saveView).toHaveBeenCalledWith(['s1', 's2'])
  })

  it('offers the scopes with active curations as the With results preset (#276)', async () => {
    userScopes.list = [{ id: 'p1', display_name: 'Private', user_role: 'curator' }]
    const { wrapper } = await mountView()
    await wrapper.find('[data-testid="scope-picker"]').trigger('click')
    await new Promise(r => setTimeout(r, 50))
    ;(document.body.querySelector('[data-testid="preset-results"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(api.getMatrix.mock.calls.at(-1)![0].scope_ids).toEqual(['s1', 's2'])
    )
  })

  it('drops unknown scope ids and caps the URL scopes at 50', async () => {
    const many = Array.from({ length: 60 }, (_, i) => ({
      id: `m${i}`,
      name: `m${i}`,
      display_name: `M${i}`,
      is_public: true
    }))
    api.getScopes.mockResolvedValue(many)
    const query = ['bogus', ...many.map(s => s.id)].map(id => `scopes=${id}`).join('&')
    await mountView(`/genes?${query}`)
    const ids = api.getMatrix.mock.calls.at(-1)![0].scope_ids
    expect(ids).toHaveLength(50)
    expect(ids).not.toContain('bogus')
    api.getMatrix.mockClear()
    await mountView('/genes?scopes=bogus')
    expect(api.getMatrix.mock.calls.at(-1)![0].scope_ids).toEqual(many.slice(0, 5).map(s => s.id))
  })

  it("lists the member's private scopes in the picker count", async () => {
    userScopes.list = [{ id: 'priv', display_name: 'Private panel', user_role: 'curator' }]
    scopesApi.fetchUserScopes.mockResolvedValue([])
    const { wrapper } = await mountView()
    useAuthStore().isAuthenticated = true
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="scope-picker"]').text()).toBe('Scopes shown: 3 of 3')
  })
})
