/**
 * AddGenesDrawer Component Tests
 *
 * @see src/components/drawers/AddGenesDrawer.vue
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import AddGenesDrawer from '../AddGenesDrawer.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const genesAPI = vi.hoisted(() => ({ createGene: vi.fn(), bulkCreateGenes: vi.fn() }))
vi.mock('@/api', () => ({ genesAPI }))

const notifications = vi.hoisted(() => ({ addToast: vi.fn() }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => notifications }))

// v-navigation-drawer needs a Vuetify layout; render its content as a plain container.
const passthrough = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  }
})

interface AddGenesVm {
  formValid: boolean
  mode: 'single' | 'bulk'
  geneData: Record<string, string>
  bulkInput: string
  bulkOptions: { skip_duplicates: boolean }
  rules: {
    required: (v: unknown) => true | string
    hgncFormat: (v: unknown) => true | string
  }
  handleSubmit: () => Promise<void>
}

let wrapper: VueWrapper | undefined

function mountDrawer(props: Record<string, unknown> = { modelValue: true }) {
  wrapper = mount(AddGenesDrawer, {
    props,
    global: { stubs: { VNavigationDrawer: passthrough } }
  })
  return wrapper
}

function vmOf(w: VueWrapper) {
  return w.vm as unknown as AddGenesVm
}

describe('AddGenesDrawer', () => {
  beforeEach(() => {
    genesAPI.createGene.mockResolvedValue({
      id: 'g1',
      hgnc_id: 'HGNC:1100',
      approved_symbol: 'BRCA1'
    })
    genesAPI.bulkCreateGenes.mockResolvedValue({ created: 2, skipped: 0, failed: 0 })
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('creates a single gene with trimmed values and reports success', async () => {
    const w = mountDrawer()
    const vm = vmOf(w)
    vm.geneData = { ...vm.geneData, hgnc_id: ' HGNC:1100 ', approved_symbol: 'BRCA1 ' }
    vm.formValid = true

    await vm.handleSubmit()
    await flushPromises()

    expect(genesAPI.createGene).toHaveBeenCalledWith({
      hgnc_id: 'HGNC:1100',
      approved_symbol: 'BRCA1'
    })
    expect(notifications.addToast).toHaveBeenCalledWith('Gene BRCA1 added successfully', 'success')
    expect(w.emitted('added')).toHaveLength(1)
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('includes optional single-gene fields only when filled', async () => {
    const w = mountDrawer()
    const vm = vmOf(w)
    vm.geneData = {
      hgnc_id: 'HGNC:1100',
      approved_symbol: 'BRCA1',
      approved_name: ' Breast cancer 1 ',
      chromosome: '17',
      location: ''
    }
    vm.formValid = true

    await vm.handleSubmit()

    expect(genesAPI.createGene).toHaveBeenCalledWith({
      hgnc_id: 'HGNC:1100',
      approved_symbol: 'BRCA1',
      approved_name: 'Breast cancer 1',
      chromosome: '17'
    })
  })

  it('does nothing when the form is invalid', async () => {
    const w = mountDrawer()
    const vm = vmOf(w)
    vm.formValid = false

    await vm.handleSubmit()

    expect(genesAPI.createGene).not.toHaveBeenCalled()
    expect(w.emitted('added')).toBeUndefined()
  })

  it('imports a bulk list parsing tab-separated, HGNC-only and symbol-only lines', async () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.5)
    const w = mountDrawer()
    const vm = vmOf(w)
    vm.mode = 'bulk'
    vm.bulkInput = 'HGNC:1100\tBRCA1\t17q21.31\n\nHGNC:1101\nTP53'
    vm.formValid = true

    await vm.handleSubmit()

    expect(genesAPI.bulkCreateGenes).toHaveBeenCalledWith({
      genes: [
        { hgnc_id: 'HGNC:1100', approved_symbol: 'BRCA1', location: '17q21.31' },
        { hgnc_id: 'HGNC:1101', approved_symbol: 'GENE1101' },
        { hgnc_id: 'HGNC:50000', approved_symbol: 'TP53' }
      ],
      skip_duplicates: true
    })
  })

  it('warns in the toast when some bulk rows failed', async () => {
    genesAPI.bulkCreateGenes.mockResolvedValue({ created: 2, skipped: 0, failed: 1 })
    const w = mountDrawer()
    const vm = vmOf(w)
    vm.mode = 'bulk'
    vm.bulkInput = 'HGNC:1100 BRCA1\nHGNC:1101 BRCA2'
    vm.formValid = true

    await vm.handleSubmit()

    expect(notifications.addToast).toHaveBeenCalledWith(
      'Added 2 genes (0 skipped, 1 failed)',
      'warning'
    )
  })

  it('shows the API detail in an error toast and keeps the drawer open', async () => {
    genesAPI.createGene.mockRejectedValue({
      message: 'Request failed',
      response: { data: { detail: 'Duplicate gene' } }
    })
    const w = mountDrawer()
    const vm = vmOf(w)
    vm.formValid = true

    await vm.handleSubmit()

    expect(notifications.addToast).toHaveBeenCalledWith(
      'Failed to add gene(s): Duplicate gene',
      'error'
    )
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to add genes',
      expect.objectContaining({ mode: 'single' })
    )
    expect(w.emitted('added')).toBeUndefined()
  })

  it('falls back to the error message when there is no API detail', async () => {
    genesAPI.createGene.mockRejectedValue({ message: 'Network down' })
    const w = mountDrawer()
    const vm = vmOf(w)
    vm.formValid = true

    await vm.handleSubmit()

    expect(notifications.addToast).toHaveBeenCalledWith(
      'Failed to add gene(s): Network down',
      'error'
    )
  })

  it('validates HGNC identifiers and required fields', () => {
    const vm = vmOf(mountDrawer())

    expect(vm.rules.hgncFormat('HGNC:1100')).toBe(true)
    expect(vm.rules.hgncFormat('')).toBe(true)
    expect(vm.rules.hgncFormat('1100')).toBe('Must be in format HGNC:#### (e.g., HGNC:1100)')
    expect(vm.rules.required('')).toBe('This field is required')
    expect(vm.rules.required('BRCA1')).toBe(true)
  })

  it('logs when the drawer opens', async () => {
    const w = mountDrawer({ modelValue: false })

    await w.setProps({ modelValue: true })

    expect(logger.debug).toHaveBeenCalledWith('AddGenesDrawer opened')
  })

  it('closes from Cancel and emits update:modelValue', async () => {
    const w = mountDrawer()
    const cancel = w.findAll('button').find(b => b.text().includes('Cancel'))

    await cancel?.trigger('click')

    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })
})
