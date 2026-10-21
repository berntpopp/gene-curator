import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import GenesTable from '@/views/GenesTable.vue'
import About from '@/views/About.vue'
import { useGenesStore } from '@/stores/genes'
import { useAuthStore } from '@/stores/auth'
import { call, vmOf } from './vm'

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }))

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: routerPush })
}))
vi.mock('@/composables/useNotifications', () => ({
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showInfo: vi.fn(),
  showWarning: vi.fn()
}))

const gene = (symbol: string, chromosome = '17') => ({
  id: symbol,
  hgnc_id: `HGNC:${symbol}`,
  approved_symbol: symbol,
  chromosome,
  location: `${chromosome}q12`,
  is_assigned: false,
  has_active_work: false
})

const mountTable = async () => {
  useAuthStore().isAuthenticated = true
  const genes = useGenesStore()
  vi.spyOn(genes, 'fetchGenes').mockImplementation(async () => {
    genes.genes = [gene('HNF1B'), gene('PKD1', 'X')] as never
    return undefined as never
  })
  const wrapper = mount(GenesTable, {
    global: { stubs: { RouterLink: RouterLinkStub } }
  })
  await flushPromises()
  return { wrapper, genes, vm: vmOf(wrapper) }
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
})

describe('GenesTable', () => {
  it('shows the store error with Retry instead of the empty state', async () => {
    useAuthStore().isAuthenticated = true
    const genes = useGenesStore()
    const fetchGenes = vi
      .spyOn(genes, 'fetchGenes')
      .mockImplementationOnce(async () => {
        genes.error = 'Request failed'
        throw new Error('500')
      })
      .mockResolvedValueOnce(undefined as never)
    const wrapper = mount(GenesTable, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(wrapper.text()).toContain('Request failed')
    expect(wrapper.text()).not.toContain('No genes available')

    await wrapper.find('button.retry').trigger('click')
    await flushPromises()
    expect(fetchGenes).toHaveBeenCalledTimes(2)
  })

  it('lists the genes with only the columns the API provides', async () => {
    const { wrapper } = await mountTable()
    const text = wrapper.text()
    expect(text).toContain('HNF1B')
    expect(text).not.toContain('Gene Family')
    expect(text).not.toContain('ClinGen Score')
    expect(text).not.toContain('Previous/Alias')
  })

  it('shows search results instead of the paged list while searching', async () => {
    const { genes, vm } = await mountTable()
    genes.searchResults = [gene('BRCA1')] as never
    vm.searchQuery = 'BR'
    await flushPromises()
    expect((vm.genes as { id: string }[]).map(g => g.id)).toEqual(['BRCA1'])
    vm.searchQuery = ''
    await flushPromises()
    expect((vm.genes as { id: string }[]).map(g => g.id)).toEqual(['HNF1B', 'PKD1'])
  })

  it('offers a static chromosome list including MT', async () => {
    const { vm } = await mountTable()
    const list = vm.chromosomes as string[]
    expect(list).toHaveLength(25)
    expect(list.slice(-3)).toEqual(['X', 'Y', 'MT'])
  })

  it('shows the server total, or the result count while searching', async () => {
    const { genes, vm, wrapper } = await mountTable()
    genes.pagination.total = 13
    await flushPromises()
    expect(wrapper.text()).toContain('13 genes')
    genes.searchResults = [gene('BRCA1')] as never
    genes.searchTotal = 42
    vm.searchQuery = 'BR'
    await flushPromises()
    expect(wrapper.text()).toContain('42 genes')
  })

  it('has no dead Add/Edit buttons and links the symbol to the gene page', async () => {
    const { wrapper } = await mountTable()
    expect(wrapper.text()).not.toContain('Add Gene')
    expect(wrapper.find('[title="Edit Gene"]').exists()).toBe(false)
    const link = wrapper.findAllComponents(RouterLinkStub).find(l => l.text() === 'HNF1B')
    expect(link?.props('to')).toEqual({ name: 'GeneDetail', params: { id: 'HNF1B' } })
  })

  it('applies header sort and page changes from the table', async () => {
    const { genes, vm } = await mountTable()
    const update = vi.spyOn(genes, 'updateSearchParams')
    await call(vm, 'handleOptions', { page: 1, sortBy: [{ key: 'approved_symbol', order: 'asc' }] })
    expect(update).not.toHaveBeenCalled()
    await call(vm, 'handleOptions', {
      page: 1,
      sortBy: [{ key: 'approved_symbol', order: 'desc' }]
    })
    expect(update).toHaveBeenCalledWith({ sort_by: 'approved_symbol', sort_order: 'desc' })
    await call(vm, 'handleOptions', { page: 3, sortBy: [] })
    expect(genes.fetchGenes).toHaveBeenLastCalledWith({ page: 3 })
  })

  it('resets to page one when filtering', async () => {
    const { genes, vm } = await mountTable()
    vm.selectedChromosome = 'X'
    const search = vi.spyOn(genes, 'searchGenes').mockResolvedValue([] as never)
    await call(vm, 'handleFilterChange')
    expect(vm.currentPage).toBe(1)
    expect(search).toHaveBeenCalledWith({
      query: '',
      chromosome: 'X',
      page: 1,
      sort_by: 'approved_symbol',
      sort_order: 'asc'
    })
  })

  it('clears filters', async () => {
    const { genes, vm } = await mountTable()
    vm.searchQuery = 'x'
    vm.selectedChromosome = '1'
    const clear = vi.spyOn(genes, 'clearSearchResults')
    call(vm, 'clearFilters')
    expect(vm.searchQuery).toBe('')
    expect(clear).toHaveBeenCalled()
  })

  it('waits for authentication before loading genes', async () => {
    const auth = useAuthStore()
    auth.isAuthenticated = false
    const genes = useGenesStore()
    const fetchGenes = vi.spyOn(genes, 'fetchGenes').mockResolvedValue(undefined as never)
    mount(GenesTable, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(fetchGenes).not.toHaveBeenCalled()
    auth.isAuthenticated = true
    await flushPromises()
    expect(fetchGenes).toHaveBeenCalledWith({ page: 1 })
  })
})

describe('GenesTable filter change', () => {
  it('searches exactly once even when the table was on page 3', async () => {
    const { genes, vm } = await mountTable()
    await call(vm, 'handleOptions', { page: 3, sortBy: [] })
    const search = vi.spyOn(genes, 'searchGenes').mockResolvedValue([] as never)
    vm.selectedChromosome = 'X'
    await call(vm, 'handleFilterChange')
    await flushPromises()
    expect(search).toHaveBeenCalledTimes(1)
  })
})

describe('GenesTable sorting while searching', () => {
  it('passes header sort to the search', async () => {
    const { genes, vm } = await mountTable()
    const search = vi.spyOn(genes, 'searchGenes').mockResolvedValue([] as never)
    vm.selectedChromosome = 'X'
    await call(vm, 'handleOptions', {
      page: 1,
      sortBy: [{ key: 'approved_symbol', order: 'desc' }]
    })
    expect(search).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort_by: 'approved_symbol', sort_order: 'desc' })
    )
  })
})

describe('static views', () => {
  it('renders the about page', () => {
    const wrapper = mount(About, { global: { stubs: { RouterLink: RouterLinkStub } } })
    expect(wrapper.text()).toContain('Gene Curator')
  })
})
