/**
 * PMIDInput Tests
 *
 * PMID normalisation, batch validation, publication display, and the
 * validity/error emits. Internals are reached through the component instance.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { publicationsAPI } from '@/api'
import type { Schema } from '@/types/api'
import PMIDInput from '../PMIDInput.vue'
import { stubVisualViewport } from './overlayStubs'

vi.mock('@/api', () => ({
  publicationsAPI: { validatePMIDs: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

type Pub = Schema<'PublicationData'>

interface PmidInternals {
  internalPMIDs: string[]
  validatedPublications: Pub[]
  validationErrors: { pmid: string; error?: string | null }[]
  errorMessages: string[]
  validatePMIDs: () => Promise<void>
  handleBlur: () => void
  handleEnter: () => void
  getChipColor: (pmid: string) => string
  getChipIcon: (pmid: string) => string
  formatAuthors: (pub: Pick<Pub, 'pmid' | 'title' | 'authors' | 'author_string'>) => string
  truncateTitle: (title: string | null | undefined, max?: number) => string
  normalizePmid: (pmid: string | null | undefined) => string
}

const pub123: Pub = {
  pmid: '123',
  title: 'A study of a gene',
  authors: ['Smith J', 'Doe A', 'Lee K', 'Roe B'],
  journal: 'Nature Genetics',
  year: 2020,
  doi: '10.1000/xyz',
  abstract: 'Short abstract',
  is_open_access: false
}

const validation = {
  total_requested: 2,
  valid_count: 1,
  invalid_count: 1,
  results: [
    { pmid: '123', is_valid: true, publication: pub123 },
    { pmid: '456', is_valid: false, error: 'not found' }
  ]
}

describe('PMIDInput', () => {
  beforeEach(() => {
    stubVisualViewport()
  })

  beforeEach(() => {
    vi.mocked(publicationsAPI.validatePMIDs).mockReset()
    vi.mocked(publicationsAPI.validatePMIDs).mockResolvedValue(validation)
  })

  function mountInput(props: Record<string, unknown> = {}) {
    const wrapper = mount(PMIDInput, { props })
    return { wrapper, vm: wrapper.vm as unknown as PmidInternals }
  }

  it('normalises PMID prefixes and whitespace', () => {
    const { vm } = mountInput()

    expect(vm.normalizePmid(' PMID:123 ')).toBe('123')
    expect(vm.normalizePmid('pmid456')).toBe('456')
    expect(vm.normalizePmid('')).toBe('')
    expect(vm.normalizePmid(null)).toBe('')
  })

  it('validates de-duplicated, normalised PMIDs in one batch', async () => {
    const { vm } = mountInput()
    vm.internalPMIDs = ['PMID:123', '123', '456']

    await vm.validatePMIDs()

    expect(publicationsAPI.validatePMIDs).toHaveBeenCalledWith(['123', '456'])
  })

  it('keeps valid PMIDs, lists invalid ones and emits the results', async () => {
    const { wrapper, vm } = mountInput()
    vm.internalPMIDs = ['123', '456']

    await vm.validatePMIDs()
    await flushPromises()

    expect(vm.internalPMIDs).toEqual(['123'])
    expect(vm.validatedPublications.map(p => p.pmid)).toEqual(['123'])
    expect(vm.validationErrors).toEqual([{ pmid: '456', error: 'not found' }])
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['123']])
    expect(wrapper.emitted('update:publications')?.at(-1)).toEqual([[pub123]])
    expect(wrapper.emitted('validated')?.at(-1)).toEqual([
      { valid: [pub123], invalid: [{ pmid: '456', error: 'not found' }] }
    ])
    expect(wrapper.text()).toContain('A study of a gene')
    expect(vm.errorMessages).toEqual(['1 invalid PMID(s)'])
  })

  it('clears everything without calling the API when no PMIDs are entered', async () => {
    const { vm } = mountInput({ publications: [pub123] })
    vm.internalPMIDs = []

    await vm.validatePMIDs()

    expect(publicationsAPI.validatePMIDs).not.toHaveBeenCalled()
    expect(vm.validatedPublications).toEqual([])
  })

  it('reports a failed validation call', async () => {
    vi.mocked(publicationsAPI.validatePMIDs).mockRejectedValueOnce(new Error('Europe PMC down'))
    const { vm } = mountInput()
    vm.internalPMIDs = ['123']

    await vm.validatePMIDs()

    expect(vm.errorMessages).toEqual(['Europe PMC down'])
  })

  it('validates on blur only when there are PMIDs that were not validated yet', async () => {
    const { vm } = mountInput({ publications: [pub123] })
    vm.internalPMIDs = ['123']
    vm.handleBlur()
    expect(publicationsAPI.validatePMIDs).not.toHaveBeenCalled()

    vm.internalPMIDs = ['123', '789']
    vm.handleBlur()
    await flushPromises()
    expect(publicationsAPI.validatePMIDs).toHaveBeenCalledTimes(1)
  })

  it('validates on Enter', async () => {
    const { vm } = mountInput()
    vm.internalPMIDs = ['123']

    vm.handleEnter()
    await flushPromises()

    expect(publicationsAPI.validatePMIDs).toHaveBeenCalledWith(['123'])
  })

  it('validates on mount when requested and PMIDs are present', () => {
    mountInput({ modelValue: ['123'], validateOnMount: true })

    expect(publicationsAPI.validatePMIDs).toHaveBeenCalledWith(['123'])
  })

  it('colours and iconises chips from the validation result', async () => {
    const { vm } = mountInput()
    vm.internalPMIDs = ['123', '456', '789']
    await vm.validatePMIDs()

    expect(vm.getChipColor('789')).toBe('default')
    expect(vm.getChipIcon('789')).toBe('')
    expect(vm.getChipColor('123')).toBe('success')
    expect(vm.getChipIcon('123')).toBe('mdi-check-circle')
    expect(vm.getChipColor('456')).toBe('error')
    expect(vm.getChipIcon('456')).toBe('mdi-alert-circle')
  })

  it('formats author lists: author_string first, then up to three then et al.', () => {
    const { vm } = mountInput()

    expect(
      vm.formatAuthors({ pmid: '1', title: 't', authors: [], author_string: 'Custom, C' })
    ).toBe('Custom, C')
    expect(vm.formatAuthors({ pmid: '1', title: 't', authors: ['A', 'B'] })).toBe('A, B')
    expect(vm.formatAuthors(pub123)).toBe('Smith J, Doe A, Lee K et al.')
    expect(vm.formatAuthors({ pmid: '1', title: 't', authors: [] })).toBe('Unknown authors')
  })

  it('truncates long titles and abstracts-style text, and names missing titles', () => {
    const { vm } = mountInput()
    const long = 'x'.repeat(100)

    expect(vm.truncateTitle(long)).toBe(`${'x'.repeat(80)}...`)
    expect(vm.truncateTitle('short')).toBe('short')
    expect(vm.truncateTitle('')).toBe('Untitled')
  })

  it('toggles the publication details and shows PubMed/DOI links', async () => {
    vi.mocked(publicationsAPI.validatePMIDs).mockResolvedValueOnce(validation)
    const { wrapper, vm } = mountInput({ publications: [pub123] })
    await flushPromises()
    expect(vm.validatedPublications).toHaveLength(1)
    expect(wrapper.find('a[href="https://pubmed.ncbi.nlm.nih.gov/123/"]').exists()).toBe(true)
    expect(wrapper.find('a[href="https://doi.org/10.1000/xyz"]').exists()).toBe(true)

    const hide = wrapper.findAll('button').find(b => b.text().includes('Hide Details'))
    await hide?.trigger('click')
    expect(wrapper.text()).not.toContain('Nature Genetics')

    const show = wrapper.findAll('button').find(b => b.text().includes('Show Details'))
    await show?.trigger('click')
    expect(wrapper.text()).toContain('Nature Genetics')
  })

  it('requires at least one PMID when marked required', () => {
    const { vm } = mountInput({ required: true })

    expect(vm.errorMessages).toEqual(['At least one PMID is required'])
  })

  it('follows external modelValue and publications changes', async () => {
    const { wrapper, vm } = mountInput({ modelValue: ['1'] })

    await wrapper.setProps({ modelValue: ['2', '3'] })
    expect(vm.internalPMIDs).toEqual(['2', '3'])

    // The fixture carries only the fields the component reads, so it is cast to the prop type
    await wrapper.setProps({ publications: [pub123] as never })
    expect(vm.validatedPublications).toEqual([pub123])
  })
})
