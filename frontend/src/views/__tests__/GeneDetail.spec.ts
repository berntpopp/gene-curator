import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  genesAPI: { getGeneById: vi.fn() },
  externalValidationAPI: { fetchHGNCGene: vi.fn() }
}))

vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  const route = reactive({ params: { id: 'gene-1' } })
  return { useRoute: () => route }
})

import { genesAPI, externalValidationAPI } from '@/api'
import { useGenesStore } from '@/stores/genes'
import GeneDetail from '@/views/GeneDetail.vue'
import { useRoute } from 'vue-router'

const localGene = {
  id: 'gene-1',
  hgnc_id: 'HGNC:1100',
  approved_symbol: 'BRCA1',
  chromosome: '17',
  location: '17q21.31',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
  alias_symbols: ['RNF53'],
  previous_symbols: []
}

const mountView = () => mount(GeneDetail, { global: { stubs: { RouterLink: true } } })

describe('GeneDetail view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(genesAPI.getGeneById).mockReset()
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockReset()
  })

  it('shows a loading state while the gene is fetched', () => {
    vi.mocked(genesAPI.getGeneById).mockReturnValue(new Promise(() => {}))
    const wrapper = mountView()
    expect(wrapper.text()).toContain('Loading gene information...')
  })

  it('shows an error when the gene cannot be loaded', async () => {
    vi.mocked(genesAPI.getGeneById).mockRejectedValue(new Error('404'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Failed to load gene information')
    expect(wrapper.text()).toContain('Failed to load gene details')
  })

  it('says "Gene not found" with a catalogue link on a 404', async () => {
    vi.mocked(genesAPI.getGeneById).mockRejectedValue({ response: { status: 404 } })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Gene not found')
    expect(wrapper.text()).not.toContain('Retry')
  })

  it('offers Retry on other failures and reloads the gene', async () => {
    vi.mocked(genesAPI.getGeneById)
      .mockRejectedValueOnce({ response: { status: 500 } })
      .mockResolvedValueOnce(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Gene not found')
    await wrapper.find('button.retry').trigger('click')
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('BRCA1')
  })

  it('renders HGNC data when the lookup succeeds', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({
      results: [
        { hgnc_id: 'HGNC:1100', symbol: 'BRCA1', name: 'BRCA1 DNA repair', status: 'Approved' }
      ]
    } as never)
    const wrapper = mountView()
    await flushPromises()
    expect(externalValidationAPI.fetchHGNCGene).toHaveBeenCalledWith('HGNC:1100')
    expect(wrapper.find('h1').text()).toBe('BRCA1')
    expect(wrapper.text()).toContain('BRCA1 DNA repair')
    expect(wrapper.text()).toContain('RNF53')
    expect(wrapper.text()).not.toContain('No alias or previous symbols recorded.')
  })

  it('keeps showing local data when the HGNC lookup fails', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockRejectedValue(new Error('down'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('BRCA1')
    expect(wrapper.text()).not.toContain('Failed to load gene information')
    expect(wrapper.text()).toContain('17q21.31')
  })

  it('loads the gene for the route id via the store', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    mountView()
    await flushPromises()
    expect(genesAPI.getGeneById).toHaveBeenCalledWith('gene-1')
    expect(useGenesStore().currentGene).toEqual(localGene)
  })

  it('reloads when the route id changes', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    mountView()
    await flushPromises()
    expect(genesAPI.getGeneById).toHaveBeenLastCalledWith('gene-1')

    useRoute().params = { id: 'gene-2' }
    await flushPromises()
    expect(genesAPI.getGeneById).toHaveBeenLastCalledWith('gene-2')
  })
})
