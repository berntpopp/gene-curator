import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/geneCatalogue', () => ({
  geneCatalogueAPI: {
    getCatalogue: vi.fn(),
    getAvailableClassifications: vi.fn(),
    getAvailableDiseases: vi.fn(),
    getAvailableScopes: vi.fn()
  }
}))

const push = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
}))

import { geneCatalogueAPI } from '@/api/geneCatalogue'
import { useGeneCatalogueStore } from '@/stores/geneCatalogue'
import GeneCatalogueView from '@/views/GeneCatalogueView.vue'
import { vmOf } from './vm'

const entry = {
  gene_id: 'g1',
  hgnc_id: 'HGNC:1100',
  approved_symbol: 'BRCA1',
  chromosome: '17',
  location: '17q21',
  total_curations: 2,
  scope_count: 1,
  classifications: { definitive: 1 },
  diseases: ['Breast cancer'],
  scope_curations: [{ scope_id: 's1', total_score: 12 }]
}

describe('GeneCatalogueView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(geneCatalogueAPI.getCatalogue).mockReset()
    vi.mocked(geneCatalogueAPI.getAvailableClassifications).mockResolvedValue([] as never)
    vi.mocked(geneCatalogueAPI.getAvailableDiseases).mockResolvedValue([] as never)
    vi.mocked(geneCatalogueAPI.getAvailableScopes).mockResolvedValue([] as never)
  })

  it('loads the catalogue and filter options on mount', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({ entries: [], total: 0 } as never)
    mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    expect(geneCatalogueAPI.getCatalogue).toHaveBeenCalled()
    expect(geneCatalogueAPI.getAvailableScopes).toHaveBeenCalled()
  })

  it('shows em dashes in the summary tiles until the summary has loaded', async () => {
    let release!: (v: never) => void
    vi.mocked(geneCatalogueAPI.getCatalogue).mockReturnValue(
      new Promise(r => (release = r as never))
    )
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    const tiles = () => wrapper.findAll('.text-h5.font-weight-bold').map(t => t.text())
    expect(tiles()).toEqual(['—', '—', '—'])
    release({
      entries: [],
      total: 0,
      summary: { total_genes_curated: 3, total_curations: 3, total_scopes: 2 }
    } as never)
    await flushPromises()
    expect(tiles()).toEqual(['3', '3', '2'])
  })

  it('shows the no-data message when there are no curated genes', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({ entries: [], total: 0 } as never)
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    expect(wrapper.text()).toContain('No curated genes found')
    expect(wrapper.text()).toContain('No genes have active curations yet')
  })

  it('renders catalogue rows from the store', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({
      entries: [entry],
      total: 1
    } as never)
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    expect(useGeneCatalogueStore().entries).toHaveLength(1)
    expect(wrapper.text()).toContain('BRCA1')
  })

  it('shows the store error instead of an empty page when the API fails', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockRejectedValue(new Error('boom'))
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    expect(wrapper.find('[data-testid="catalogue-error"]').exists()).toBe(true)
  })

  it('navigates to the registered scope-dashboard route', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({ entries: [], total: 0 } as never)
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    const vm = wrapper.vm as unknown as { navigateToScope: (c: { scope_id: string }) => void }
    vm.navigateToScope({ scope_id: 's1' })
    expect(push).toHaveBeenCalledWith({ name: 'scope-dashboard', params: { scopeId: 's1' } })
  })

  it('builds scope filter options from the API id and display_name', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({ entries: [], total: 0 } as never)
    vi.mocked(geneCatalogueAPI.getAvailableScopes).mockResolvedValue([
      { id: 's1', name: 'kidney', display_name: 'Kidney Genetics' }
    ] as never)
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    expect(vmOf(wrapper).scopeOptions).toEqual([{ title: 'Kidney Genetics', value: 's1' }])
  })

  it('has one footer, shows the server total and truncates a single long disease', async () => {
    const long = 'D'.repeat(120)
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({
      entries: [{ ...entry, diseases: [long] }],
      total: 600
    } as never)
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    expect(wrapper.findAll('.v-data-table-footer')).toHaveLength(1)
    expect(wrapper.text()).toContain('of 600')
    expect(wrapper.find(`.disease-cell[title="${long}"]`).exists()).toBe(true)
  })

  it('passes table page and sort to the store and refetches', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({
      entries: [entry],
      total: 600
    } as never)
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    const handle = vmOf(wrapper).handleOptions as (o: unknown) => Promise<void>
    await handle({ page: 3, sortBy: [{ key: 'total_curations', order: 'desc' }] })
    const store = useGeneCatalogueStore()
    expect(store.filters.sortBy).toBe('total_curations')
    expect(store.filters.sortOrder).toBe('desc')
    expect(geneCatalogueAPI.getCatalogue).toHaveBeenLastCalledWith(
      expect.objectContaining({ skip: 40, sort_by: 'total_curations', sort_order: 'desc' })
    )
  })

  it('a filter change fetches exactly once, even from page 3', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({
      entries: [entry],
      total: 600
    } as never)
    const wrapper = mount(GeneCatalogueView, { global: { stubs: { RouterLink: true } } })
    await flushPromises()
    await (vmOf(wrapper).handleOptions as (o: unknown) => Promise<void>)({
      page: 3,
      sortBy: []
    })
    vi.mocked(geneCatalogueAPI.getCatalogue).mockClear()
    vmOf(wrapper).selectedScope = 's1'
    await (vmOf(wrapper).handleFilterChange as () => Promise<void>)()
    await flushPromises()
    expect(geneCatalogueAPI.getCatalogue).toHaveBeenCalledTimes(1)
  })

  it('opens the quick info dialog for a gene and navigates from it', async () => {
    vi.mocked(geneCatalogueAPI.getCatalogue).mockResolvedValue({ entries: [], total: 0 } as never)
    const wrapper = mount(GeneCatalogueView, {
      global: {
        stubs: {
          RouterLink: true,
          VDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }
        }
      }
    })
    await flushPromises()
    const vm = vmOf(wrapper)
    ;(vm.showQuickInfo as (e: unknown) => void)({
      ...entry,
      scope_curations: [
        { scope_id: 's1', scope_name: 'Kidney', classification: 'definitive', is_public: true }
      ]
    })
    await flushPromises()
    expect(wrapper.text()).toContain('HGNC:1100')
    expect(wrapper.text()).toContain('Associated Diseases (1)')
    const view = wrapper.findAll('button').find(b => b.text().includes('View'))
    await view?.trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'GeneDetail', params: { id: 'g1' } })
  })
})
