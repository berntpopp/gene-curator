/**
 * MONDOAutocomplete Tests
 *
 * Debounced disease search, selection emits, and restoring a saved MONDO ID.
 * Search and selection internals are reached through the component instance.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ontologyAPI } from '@/api'
import MONDOAutocomplete from '../MONDOAutocomplete.vue'

vi.mock('@/api', () => ({
  ontologyAPI: { searchMONDO: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface Term {
  mondo_id: string
  label: string
  definition?: string | null
  displayText?: string
}

interface MondoInternals {
  searchResults: Term[]
  selectedItem: Term | null
  selectedId: Term | null
  errorMessages: string[]
  performSearch: (query: string) => Promise<void>
  handleSearch: (query: string | null | undefined) => void
  handleSelect: (item: Term | null | undefined) => void
}

const hit = {
  mondo_id: 'MONDO:0001073',
  label: 'Intellectual disability',
  definition: 'Impaired cognition',
  synonyms: [],
  xrefs: []
}

describe('MONDOAutocomplete', () => {
  beforeEach(() => {
    vi.mocked(ontologyAPI.searchMONDO).mockReset()
    vi.mocked(ontologyAPI.searchMONDO).mockResolvedValue({
      query: 'intel',
      total_results: 1,
      results: [hit]
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function mountAutocomplete(props: Record<string, unknown> = {}) {
    const wrapper = mount(MONDOAutocomplete, { props })
    return { wrapper, vm: wrapper.vm as unknown as MondoInternals }
  }

  it('searches with the limit and maps hits to display text', async () => {
    const { vm } = mountAutocomplete({ maxResults: 5 })

    await vm.performSearch('intel')

    expect(ontologyAPI.searchMONDO).toHaveBeenCalledWith('intel', 5)
    expect(vm.searchResults[0]?.displayText).toBe('Intellectual disability (MONDO:0001073)')
  })

  it('does not search for queries shorter than the minimum length', async () => {
    const { vm } = mountAutocomplete()

    await vm.performSearch('i')

    expect(ontologyAPI.searchMONDO).not.toHaveBeenCalled()
    expect(vm.searchResults).toEqual([])
  })

  it('debounces typing into a single search', async () => {
    vi.useFakeTimers()
    const { vm } = mountAutocomplete()

    vm.handleSearch('in')
    vm.handleSearch('intel')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(ontologyAPI.searchMONDO).toHaveBeenCalledTimes(1)
    expect(ontologyAPI.searchMONDO).toHaveBeenCalledWith('intel', 15)
  })

  it('skips searching when the query is the label of the current selection', async () => {
    vi.useFakeTimers()
    const { vm } = mountAutocomplete()
    vm.handleSelect(hit)

    vm.handleSearch('Intellectual disability')
    await vi.advanceTimersByTimeAsync(300)

    expect(ontologyAPI.searchMONDO).not.toHaveBeenCalled()
  })

  it('reports a failed search and clears the results', async () => {
    vi.mocked(ontologyAPI.searchMONDO).mockRejectedValueOnce(new Error('timeout'))
    const { vm } = mountAutocomplete()

    await vm.performSearch('intel')

    expect(vm.searchResults).toEqual([])
    expect(vm.errorMessages).toEqual(['Search failed'])
  })

  it('emits the MONDO ID and label on selection, and empties both on clear', () => {
    const { wrapper, vm } = mountAutocomplete()

    vm.handleSelect(hit)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['MONDO:0001073'])
    expect(wrapper.emitted('update:diseaseName')?.at(-1)).toEqual(['Intellectual disability'])
    expect(wrapper.emitted('select')?.at(-1)).toEqual([hit])

    vm.handleSelect(null)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
    expect(wrapper.emitted('update:diseaseName')?.at(-1)).toEqual([''])
    expect(wrapper.emitted('select')?.at(-1)).toEqual([null])
  })

  it('restores the saved term on mount by looking it up by ID', async () => {
    const { vm } = mountAutocomplete({ modelValue: 'MONDO:0001073' })
    await flushPromises()

    expect(ontologyAPI.searchMONDO).toHaveBeenCalledWith('MONDO:0001073', 1)
    expect(vm.selectedItem?.label).toBe('Intellectual disability')
  })

  it('shows a placeholder for a saved ID while the lookup is pending or empty', async () => {
    vi.mocked(ontologyAPI.searchMONDO).mockResolvedValueOnce({
      query: 'MONDO:9',
      total_results: 0,
      results: []
    })
    const { vm } = mountAutocomplete({ modelValue: 'MONDO:9', diseaseName: 'Rare thing' })
    await flushPromises()

    expect(vm.selectedItem).toBeNull()
    expect(vm.selectedId?.mondo_id).toBe('MONDO:9')
    expect(vm.selectedId?.displayText).toBe('Rare thing (MONDO:9)')
  })

  it('ignores a failed restore lookup', async () => {
    vi.mocked(ontologyAPI.searchMONDO).mockRejectedValueOnce(new Error('offline'))
    const { vm } = mountAutocomplete({ modelValue: 'MONDO:1' })
    await flushPromises()

    expect(vm.selectedItem).toBeNull()
  })

  it('requires a disease when marked required', () => {
    const { vm } = mountAutocomplete({ required: true })

    expect(vm.errorMessages).toEqual(['MONDO disease is required'])
  })
})
