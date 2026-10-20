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
})
