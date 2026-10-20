import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AddGeneModal from '../AddGeneModal.vue'
import { genesAPI, assignmentsAPI } from '@/api'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())
const hgnc = vi.hoisted(() => ({
  search: vi.fn(),
  validateBulk: vi.fn()
}))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/composables/useHgncSearch', async () => {
  const { ref } = await import('vue')
  return {
    useHgncSearch: () => ({
      results: ref([]),
      isSearching: ref(false),
      search: hgnc.search,
      validateBulk: hgnc.validateBulk
    })
  }
})
vi.mock('@/api', () => ({
  genesAPI: { createGene: vi.fn(), bulkCreateGenes: vi.fn() },
  assignmentsAPI: { createAssignment: vi.fn(), bulkAssignGenes: vi.fn() }
}))

const createGene = vi.mocked(genesAPI.createGene)
const createAssignment = vi.mocked(assignmentsAPI.createAssignment)

const brca1 = {
  hgnc_id: 'HGNC:1100',
  symbol: 'BRCA1',
  name: 'BRCA1 gene',
  alias_symbols: [],
  previous_symbols: []
}
const brca2 = {
  hgnc_id: 'HGNC:1101',
  symbol: 'BRCA2',
  name: 'BRCA2 gene',
  alias_symbols: [],
  previous_symbols: []
}

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

/** Internal state read through wrapper.vm. */
interface AddGeneVm {
  mode: 'single' | 'bulk'
  searchQuery: string
  selectedGene: typeof brca1 | null
  bulkInput: string
  skipDuplicates: boolean
  bulkValidationResults: Array<{ status: string; gene?: unknown; alternatives?: unknown[] }>
  canSubmit: boolean
  submitButtonText: string
  bulkValidationSummary: { valid: number; invalid: number; suggestions: number }
  handleSearchUpdate(query: string): Promise<void>
  validateBulkGenes(): Promise<void>
  acceptSuggestion(idx: number): void
  selectAlternative(idx: number, alt: typeof brca1): void
  handleSubmit(): Promise<void>
  handleCancel(): void
}

function internals(wrapper: { vm: unknown }): AddGeneVm {
  return wrapper.vm as AddGeneVm
}

async function mountModal(props: Record<string, unknown> = {}) {
  const wrapper = mount(AddGeneModal, {
    props: { modelValue: false, scopeId: 'scope-1', ...props },
    global: { stubs: { VDialog: dialogStub } }
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  return wrapper
}

describe('AddGeneModal', () => {
  beforeEach(() => {
    createGene.mockReset()
    createAssignment.mockReset()
    hgnc.search.mockReset()
    hgnc.validateBulk.mockReset()
    addToast.mockReset()
    logger.error.mockReset()
  })

  it('searches HGNC only for queries of at least two characters', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    await vm.handleSearchUpdate('B')
    expect(hgnc.search).not.toHaveBeenCalled()

    await vm.handleSearchUpdate('BR')
    expect(hgnc.search).toHaveBeenCalledWith('BR')
  })

  it('cannot submit a single gene until one is selected', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    expect(vm.canSubmit).toBe(false)
    expect(vm.submitButtonText).toBe('Add Gene')

    vm.selectedGene = brca1
    await flushPromises()

    expect(vm.canSubmit).toBe(true)
  })

  it('adds the selected gene and closes', async () => {
    createGene.mockResolvedValue({
      id: 'g-1',
      hgnc_id: 'HGNC:1100',
      approved_symbol: 'BRCA1'
    } as never)
    createAssignment.mockResolvedValue({} as never)
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.selectedGene = brca1
    await flushPromises()
    await vm.handleSubmit()

    expect(createGene).toHaveBeenCalledWith(expect.objectContaining({ hgnc_id: 'HGNC:1100' }))
    expect(wrapper.emitted('added')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('reports a failed add with the server detail and keeps the modal open', async () => {
    createGene.mockRejectedValue({ message: 'x', response: { data: { detail: 'Duplicate' } } })
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.selectedGene = brca1
    await flushPromises()
    await vm.handleSubmit()

    expect(logger.error).toHaveBeenCalledWith('Failed to add genes', { error: 'x', mode: 'single' })
    expect(addToast).toHaveBeenCalledWith('Failed to add gene(s): Duplicate', 'error')
    expect(wrapper.emitted('added')).toBeUndefined()
  })

  it('validates a pasted list in bulk mode and summarises the results', async () => {
    hgnc.validateBulk.mockResolvedValue({
      valid: [brca1],
      invalid: [],
      results: [
        { status: 'valid', gene: brca1 },
        { status: 'suggestion', gene: brca2, alternatives: [brca1] },
        { status: 'not_found', gene: null }
      ]
    })
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.mode = 'bulk'
    vm.bulkInput = 'BRCA1, BRCA2\nNOPE'
    await vm.validateBulkGenes()
    await flushPromises()

    expect(hgnc.validateBulk).toHaveBeenCalledWith(['BRCA1', 'BRCA2', 'NOPE'])
    expect(vm.bulkValidationSummary).toEqual({ valid: 1, invalid: 1, suggestions: 1 })
    expect(vm.canSubmit).toBe(true)
    expect(vm.submitButtonText).toBe('Add 2 Genes')
  })

  it('accepts a suggestion and then adds the bulk genes', async () => {
    hgnc.validateBulk.mockResolvedValue({
      valid: [],
      invalid: [],
      results: [{ status: 'suggestion', gene: brca2 }]
    })
    vi.mocked(genesAPI.bulkCreateGenes).mockResolvedValue({
      created_genes: [],
      total_created: 1,
      total_skipped: 0,
      total_errors: 0
    } as never)
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.mode = 'bulk'
    vm.bulkInput = 'BRCA2'
    await vm.validateBulkGenes()
    vm.acceptSuggestion(0)
    expect(vm.bulkValidationResults[0]?.status).toBe('valid')

    await vm.handleSubmit()

    expect(genesAPI.bulkCreateGenes).toHaveBeenCalledWith({
      genes: [expect.objectContaining({ hgnc_id: 'HGNC:1101', approved_symbol: 'BRCA2' })],
      validate_hgnc: true,
      skip_duplicates: true
    })
    expect(addToast).toHaveBeenCalledWith('Added 1 genes (0 skipped, 0 failed)', 'success')
  })

  it('lets the user pick an alternative for a suggestion', async () => {
    hgnc.validateBulk.mockResolvedValue({
      valid: [],
      invalid: [],
      results: [{ status: 'suggestion', gene: brca2, alternatives: [brca1] }]
    })
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.mode = 'bulk'
    vm.bulkInput = 'BRCA2'
    await vm.validateBulkGenes()
    vm.selectAlternative(0, brca1)

    expect(vm.bulkValidationResults[0]).toMatchObject({ status: 'valid', gene: brca1 })
  })

  it('ignores accept and alternative actions for unknown rows', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    expect(() => vm.acceptSuggestion(5)).not.toThrow()
    expect(() => vm.selectAlternative(5, brca1)).not.toThrow()
  })

  it('reports a failed bulk validation', async () => {
    hgnc.validateBulk.mockRejectedValue({ message: 'down' })
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.bulkInput = 'BRCA1'
    await vm.validateBulkGenes()

    expect(logger.error).toHaveBeenCalledWith('Bulk validation error', { error: 'down' })
    expect(addToast).toHaveBeenCalledWith('Failed to validate genes', 'error')
  })

  it('skips validation for blank input', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.bulkInput = '   '
    await vm.validateBulkGenes()

    expect(hgnc.validateBulk).not.toHaveBeenCalled()
  })

  it('clears previous validation results when the input changes', async () => {
    hgnc.validateBulk.mockResolvedValue({
      valid: [],
      invalid: [],
      results: [{ status: 'valid', gene: brca1 }]
    })
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.bulkInput = 'BRCA1'
    await vm.validateBulkGenes()
    expect(vm.bulkValidationResults).toHaveLength(1)

    vm.bulkInput = 'BRCA1,BRCA2'
    await flushPromises()
    expect(vm.bulkValidationResults).toEqual([])
  })

  it('resets the form each time the modal opens', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)
    vm.selectedGene = brca1
    vm.searchQuery = 'BRCA'

    await wrapper.setProps({ modelValue: false })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    expect(vm.selectedGene).toBeNull()
    expect(vm.searchQuery).toBe('')
    expect(vm.mode).toBe('single')
  })

  it('emits close when cancelled', async () => {
    const wrapper = await mountModal()

    internals(wrapper).handleCancel()

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })
})
