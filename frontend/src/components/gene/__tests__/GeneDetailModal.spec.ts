import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GeneDetailModal from '../GeneDetailModal.vue'
import { externalValidationAPI } from '@/api'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/api', () => ({ externalValidationAPI: { fetchHGNCGene: vi.fn() } }))

const fetchHGNCGene = vi.mocked(externalValidationAPI.fetchHGNCGene)

const brca1 = {
  hgnc_id: 'HGNC:1100',
  symbol: 'BRCA1',
  name: 'BRCA1 DNA repair associated',
  status: 'Approved',
  locus_type: 'gene with protein product',
  chromosome: '17',
  location: '17q21.31',
  alias_symbols: ['RNF53'],
  previous_symbols: ['BRCAI']
}

// v-dialog teleports its content; render it inline and only while open.
const dialogStub = {
  props: ['modelValue'],
  template: '<div v-if="modelValue"><slot /></div>'
}

function mountModal(props: Record<string, unknown> = {}) {
  return mount(GeneDetailModal, {
    props: { modelValue: true, hgncId: 'HGNC:1100', geneSymbol: 'BRCA1', ...props },
    global: { stubs: { VDialog: dialogStub } }
  })
}

describe('GeneDetailModal', () => {
  beforeEach(() => {
    fetchHGNCGene.mockReset()
    logger.debug.mockReset()
    logger.error.mockReset()
  })

  it('fetches the gene from HGNC when opened and shows its fields', async () => {
    fetchHGNCGene.mockResolvedValue({ results: [brca1] } as never)

    const wrapper = mountModal()
    await flushPromises()

    expect(fetchHGNCGene).toHaveBeenCalledWith('HGNC:1100')
    expect(wrapper.text()).toContain('BRCA1 DNA repair associated')
    expect(wrapper.text()).toContain('17q21.31')
    expect(wrapper.text()).toContain('RNF53')
    expect(wrapper.text()).toContain('BRCAI')
    expect(wrapper.text()).toContain('Approved')
    expect(logger.debug).toHaveBeenCalledWith('Gene data fetched', {
      hgnc_id: 'HGNC:1100',
      symbol: 'BRCA1'
    })
  })

  it('links to the HGNC report and to the full gene page when a gene id is given', async () => {
    fetchHGNCGene.mockResolvedValue({ results: [brca1] } as never)

    const wrapper = mountModal({ geneId: 'g-1' })
    await flushPromises()

    const hgnc = wrapper.find('a[href*="genenames.org"]')
    expect(hgnc.attributes('href')).toBe(
      'https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:1100'
    )
    expect(wrapper.text()).toContain('Full details')
  })

  it('says when no alias or previous symbols are recorded', async () => {
    fetchHGNCGene.mockResolvedValue({
      results: [{ ...brca1, alias_symbols: [], previous_symbols: [] }]
    } as never)

    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.text()).toContain('No alias or previous symbols recorded.')
  })

  it('shows an error when HGNC has no matching gene', async () => {
    fetchHGNCGene.mockResolvedValue({ results: [] } as never)

    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.text()).toContain('Gene not found in HGNC database')
  })

  it('shows and logs the error when the request fails', async () => {
    fetchHGNCGene.mockRejectedValue(new Error('HGNC down'))

    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.text()).toContain('HGNC down')
    expect(logger.error).toHaveBeenCalledWith('Failed to fetch gene data', {
      hgnc_id: 'HGNC:1100',
      error: 'HGNC down'
    })
  })

  it('uses a generic message when the failure carries no message', async () => {
    fetchHGNCGene.mockRejectedValue({})

    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.text()).toContain('Failed to fetch gene information')
  })

  it('shows a loading state while the request is pending', () => {
    fetchHGNCGene.mockReturnValue(new Promise(() => {}) as never)

    const wrapper = mountModal()

    expect(wrapper.text()).toContain('Loading gene information from HGNC...')
  })

  it('does not fetch while closed and fetches when opened', async () => {
    fetchHGNCGene.mockResolvedValue({ results: [brca1] } as never)

    const wrapper = mountModal({ modelValue: false })
    await flushPromises()
    expect(fetchHGNCGene).not.toHaveBeenCalled()

    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    expect(fetchHGNCGene).toHaveBeenCalledTimes(1)
  })

  it('refetches when the HGNC id changes while open', async () => {
    fetchHGNCGene.mockResolvedValue({ results: [brca1] } as never)

    const wrapper = mountModal()
    await flushPromises()
    await wrapper.setProps({ hgncId: 'HGNC:5' })
    await flushPromises()

    expect(fetchHGNCGene).toHaveBeenLastCalledWith('HGNC:5')
  })

  it('emits update:modelValue false when closed', async () => {
    fetchHGNCGene.mockResolvedValue({ results: [brca1] } as never)

    const wrapper = mountModal()
    await flushPromises()
    await wrapper
      .findAll('button')
      .find(b => b.text().trim() === 'Close')!
      .trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])
  })
})
