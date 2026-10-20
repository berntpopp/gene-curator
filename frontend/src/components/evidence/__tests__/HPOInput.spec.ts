/**
 * HPOInput Tests
 *
 * Batch validation of HPO term IDs on blur/Enter, chip state, and the
 * store-cache fallback for term names. Validation is reached through the
 * component instance because it is not rendered directly.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useExternalValidationStore } from '@/stores/externalValidation'
import HPOInput from '../HPOInput.vue'
import { stubVisualViewport } from './overlayStubs'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface HPOInputInternals {
  internalTerms: string[]
  validateTerms: () => Promise<void>
  getChipColor: (term: string) => string
  getChipIcon: (term: string) => string
  getTermName: (term: string) => string
  handleBlur: () => void
  handleEnter: () => void
}

const validResult = {
  is_valid: true,
  status: 'valid',
  data: { term_name: 'Abnormality', definition: 'A def' }
}
const invalidResult = { is_valid: false, status: 'invalid', data: null }

describe('HPOInput', () => {
  beforeEach(() => {
    stubVisualViewport()
  })

  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  function mountInput(props: Record<string, unknown> = {}) {
    const wrapper = mount(HPOInput, { props, global: { plugins: [pinia] } })
    return { wrapper, vm: wrapper.vm as unknown as HPOInputInternals }
  }

  it('validates all terms in one batch and reports valid/invalid counts', async () => {
    const store = useExternalValidationStore()
    const spy = vi
      .spyOn(store, 'validateBatch')
      .mockResolvedValue({ 'HP:0000001': validResult, 'HP:0000002': invalidResult })
    const { wrapper, vm } = mountInput({ modelValue: ['HP:0000001', 'HP:0000002'] })

    await vm.validateTerms()
    await flushPromises()

    expect(spy).toHaveBeenCalledWith('hpo', ['HP:0000001', 'HP:0000002'])
    expect(vm.getTermName('HP:0000001')).toBe('Abnormality')
    expect(wrapper.text()).toContain('1 valid')
    expect(wrapper.text()).toContain('1 invalid')
    expect(wrapper.text()).toContain('1 invalid HPO term(s)')
  })

  it('clears results without calling the API when there are no terms', async () => {
    const store = useExternalValidationStore()
    const spy = vi.spyOn(store, 'validateBatch')
    const { vm } = mountInput({ modelValue: [] })

    await vm.validateTerms()

    expect(spy).not.toHaveBeenCalled()
  })

  it('shows the error message from a failed batch, or a generic fallback', async () => {
    const store = useExternalValidationStore()
    vi.spyOn(store, 'validateBatch').mockRejectedValueOnce(new Error('network down'))
    const { wrapper, vm } = mountInput({ modelValue: ['HP:0000001'] })

    await vm.validateTerms()
    await flushPromises()
    expect(wrapper.text()).toContain('network down')

    vi.spyOn(store, 'validateBatch').mockRejectedValueOnce('boom')
    await vm.validateTerms()
    await flushPromises()
    expect(wrapper.text()).toContain('HPO validation failed')
  })

  it('requires at least one term when marked required', () => {
    const { wrapper } = mountInput({ required: true, modelValue: [] })

    expect(wrapper.text()).toContain('At least one HPO term is required')
  })

  it('validates on mount when requested', () => {
    const store = useExternalValidationStore()
    const spy = vi.spyOn(store, 'validateBatch').mockResolvedValue({})

    mountInput({ modelValue: ['HP:0000001'], validateOnMount: true })

    expect(spy).toHaveBeenCalledWith('hpo', ['HP:0000001'])
  })

  it('emits update:modelValue when the terms change and follows external updates', async () => {
    const { wrapper, vm } = mountInput({ modelValue: ['HP:0000001'] })

    vm.internalTerms = ['HP:0000001', 'HP:0000009']
    await flushPromises()
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['HP:0000001', 'HP:0000009']])

    await wrapper.setProps({ modelValue: ['HP:0000042'] })
    expect(vm.internalTerms).toEqual(['HP:0000042'])
  })

  it('colours chips by validation state and shows a spinner while validating', async () => {
    const store = useExternalValidationStore()
    vi.spyOn(store, 'validateBatch').mockResolvedValue({
      'HP:0000001': validResult,
      'HP:0000002': invalidResult
    })
    const { vm } = mountInput({ modelValue: ['HP:0000001', 'HP:0000002', 'HP:0000003'] })

    expect(vm.getChipColor('HP:0000003')).toBe('default')
    expect(vm.getChipIcon('HP:0000003')).toBe('')

    await vm.validateTerms()
    expect(vm.getChipColor('HP:0000001')).toBe('success')
    expect(vm.getChipIcon('HP:0000001')).toBe('mdi-check-circle')
    expect(vm.getChipColor('HP:0000002')).toBe('error')
    expect(vm.getChipIcon('HP:0000002')).toBe('mdi-alert-circle')
  })

  it('falls back to the store cache for term names not validated in this component', () => {
    // The store keys its cache by "<validator>:<lowercased value>"
    const store = useExternalValidationStore()
    store.cache.set('hpo:hp:0000123', {
      is_valid: true,
      status: 'valid',
      data: { term_name: 'Cached term' }
    })
    const { vm } = mountInput()

    expect(vm.getTermName('HP:0000123')).toBe('Cached term')
    expect(vm.getTermName('HP:0000999')).toBe('')
  })

  it('validates on blur and on Enter', async () => {
    const store = useExternalValidationStore()
    const spy = vi.spyOn(store, 'validateBatch').mockResolvedValue({})
    const { vm } = mountInput({ modelValue: ['HP:0000001'] })

    vm.handleBlur()
    vm.handleEnter()
    await flushPromises()

    expect(spy).toHaveBeenCalledTimes(2)
  })

  it('opens the validation summary and lists the valid terms', async () => {
    const store = useExternalValidationStore()
    vi.spyOn(store, 'validateBatch').mockResolvedValue({
      'HP:0000001': validResult,
      'HP:0000002': invalidResult
    })
    const { wrapper, vm } = mountInput({ modelValue: ['HP:0000001', 'HP:0000002'] })
    await vm.validateTerms()
    await flushPromises()

    await wrapper.find('button[aria-label*="valid"]').trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('HPO Validation Summary')
    expect(document.body.textContent).toContain('Valid Terms')
  })
})
