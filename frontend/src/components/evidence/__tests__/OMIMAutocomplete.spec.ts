/**
 * OMIMAutocomplete Tests
 *
 * Single and multiple OMIM selection, restoring saved IDs, the detail dialog,
 * and search. Internals are reached through the component instance.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ontologyAPI } from '@/api'
import OMIMAutocomplete from '../OMIMAutocomplete.vue'
import { stubVisualViewport } from './overlayStubs'

vi.mock('@/api', () => ({
  ontologyAPI: { searchOMIM: vi.fn(), getOMIMDisease: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface Disease {
  omim_id: string
  name: string
  mondo_id?: string | null
  gene_symbols?: string[]
  displayText?: string
}

interface OmimInternals {
  searchResults: Disease[]
  selectedItems: Disease | Disease[] | null
  showDetailDialog: boolean
  detailDisease: { omim_id: string; name: string; error?: string } | null
  errorMessages: string[]
  performSearch: (query: string) => Promise<void>
  handleSelect: (items: Disease | Disease[] | null | undefined) => void
  loadOMIMDetails: (omimId: string) => Promise<void>
}

const hit = {
  omim_id: 'OMIM:300855',
  name: 'Ogden syndrome',
  mondo_id: 'MONDO:1',
  gene_symbols: ['NAA10']
}

describe('OMIMAutocomplete', () => {
  beforeEach(() => {
    stubVisualViewport()
  })

  beforeEach(() => {
    vi.mocked(ontologyAPI.searchOMIM).mockReset()
    vi.mocked(ontologyAPI.searchOMIM).mockResolvedValue({
      query: 'ogden',
      total_results: 1,
      results: [hit]
    })
    vi.mocked(ontologyAPI.getOMIMDisease).mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function mountOmim(props: Record<string, unknown> = {}) {
    const wrapper = mount(OMIMAutocomplete, { props })
    return { wrapper, vm: wrapper.vm as unknown as OmimInternals }
  }

  it('searches and maps hits to display text', async () => {
    const { vm } = mountOmim()

    await vm.performSearch('ogden')

    expect(ontologyAPI.searchOMIM).toHaveBeenCalledWith('ogden', 15)
    expect(vm.searchResults[0]?.displayText).toBe('Ogden syndrome (OMIM:300855)')
  })

  it('does not search for short queries and reports failed searches', async () => {
    const { vm } = mountOmim()

    await vm.performSearch('o')
    expect(ontologyAPI.searchOMIM).not.toHaveBeenCalled()

    vi.mocked(ontologyAPI.searchOMIM).mockRejectedValueOnce(new Error('boom'))
    await vm.performSearch('ogden')
    expect(vm.searchResults).toEqual([])
    expect(vm.errorMessages).toEqual(['Search failed'])
  })

  it('emits one ID for single selection and an empty string when cleared', () => {
    const { wrapper, vm } = mountOmim()

    vm.handleSelect(hit)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['OMIM:300855'])
    expect(wrapper.emitted('select')?.at(-1)).toEqual([hit])

    vm.handleSelect(null)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
  })

  it('emits the list of IDs for multiple selection', () => {
    const { wrapper, vm } = mountOmim({ multiple: true })
    const second = { omim_id: 'OMIM:600000', name: 'Other' }

    vm.handleSelect([hit, second])
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['OMIM:300855', 'OMIM:600000']])

    vm.handleSelect(null)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([[]])
  })

  it('restores a saved single ID on mount', async () => {
    const { vm } = mountOmim({ modelValue: 'OMIM:300855' })
    await flushPromises()

    expect(ontologyAPI.searchOMIM).toHaveBeenCalledWith('OMIM:300855', 1)
    expect((vm.selectedItems as Disease).name).toBe('Ogden syndrome')
  })

  it('restores saved multiple IDs and keeps placeholders for unknown ones', async () => {
    vi.mocked(ontologyAPI.searchOMIM)
      .mockResolvedValueOnce({ query: 'a', total_results: 1, results: [hit] })
      .mockResolvedValueOnce({ query: 'b', total_results: 0, results: [] })
      .mockRejectedValueOnce(new Error('offline'))
    const { vm } = mountOmim({
      multiple: true,
      modelValue: ['OMIM:300855', 'OMIM:999998', 'OMIM:999999']
    })
    await flushPromises()

    const items = vm.selectedItems as Disease[]
    expect(items.map(i => i.omim_id)).toEqual(['OMIM:300855', 'OMIM:999998', 'OMIM:999999'])
    expect(items[1]?.displayText).toBe('OMIM:999998')
    expect(items[2]?.name).toBe('OMIM:999999')
  })

  it('opens the detail dialog and loads the full record', async () => {
    vi.mocked(ontologyAPI.getOMIMDisease).mockResolvedValueOnce({
      omim_id: 'OMIM:300855',
      name: 'Ogden syndrome',
      genes: [{ gene_id: '1', symbol: 'NAA10' }],
      phenotypes: { 'Clinical synopsis': [{ hpo_id: 'HP:1', name: 'Hypotonia', sources: [] }] }
    })
    const { vm } = mountOmim()

    await vm.loadOMIMDetails('OMIM:300855')

    expect(vm.showDetailDialog).toBe(true)
    expect(vm.detailDisease?.name).toBe('Ogden syndrome')
  })

  it('shows a failure record in the dialog when details cannot be loaded', async () => {
    vi.mocked(ontologyAPI.getOMIMDisease).mockRejectedValueOnce(new Error('404'))
    const { vm } = mountOmim()

    await vm.loadOMIMDetails('OMIM:1')

    expect(vm.detailDisease).toEqual({ omim_id: 'OMIM:1', name: 'Failed to load', error: '404' })
  })

  it('requires a value when marked required', () => {
    expect(mountOmim({ required: true, multiple: true, modelValue: [] }).vm.errorMessages).toEqual([
      'At least one OMIM disease is required'
    ])
    expect(mountOmim({ required: true, modelValue: '' }).vm.errorMessages).toEqual([
      'OMIM disease is required'
    ])
  })
})
