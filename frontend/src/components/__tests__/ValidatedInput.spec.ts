/**
 * ValidatedInput Component Tests
 *
 * useValidation() is mocked so each test controls the validation state.
 *
 * @see src/components/ValidatedInput.vue
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Ref } from 'vue'
import ValidatedInput from '../ValidatedInput.vue'
import { installVisualViewport } from './overlay-env'

installVisualViewport()

interface ValidationState {
  value: Ref<string>
  result: Ref<unknown>
  isValidating: Ref<boolean>
  error: Ref<unknown>
}

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const validation = vi.hoisted(() => ({}) as Record<string, unknown>)
vi.mock('@/composables/useValidation', async () => {
  const { ref } = await import('vue')
  return {
    useValidation: () => {
      validation.value = ref('')
      validation.result = ref(null)
      validation.isValidating = ref(false)
      validation.error = ref(null)
      return validation
    }
  }
})

const state = validation as unknown as ValidationState

let wrapper: VueWrapper | undefined

function mountInput(props: Record<string, unknown> = {}) {
  wrapper = mount(ValidatedInput, {
    props: { modelValue: 'BRCA1', validator: 'hgnc', label: 'Gene', ...props },
    attachTo: document.body
  })
  return wrapper
}

describe('ValidatedInput', () => {
  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
    vi.clearAllMocks()
  })

  it('syncs the initial modelValue into the validation input', () => {
    mountInput({ modelValue: 'TP53' })

    expect(state.value.value).toBe('TP53')
  })

  it('emits update:modelValue when the user types', async () => {
    const w = mountInput()

    await w.find('input').setValue('BRCA2')
    await w.vm.$nextTick()

    expect(w.emitted('update:modelValue')?.at(-1)).toEqual(['BRCA2'])
  })

  it('re-emits the value and logs on blur', async () => {
    const w = mountInput()

    await w.find('input').trigger('blur')

    expect(w.emitted('update:modelValue')?.at(-1)).toEqual(['BRCA1'])
    expect(logger.debug).toHaveBeenCalledWith(
      'Validated input blur',
      expect.objectContaining({ validator: 'hgnc', value: 'BRCA1' })
    )
  })

  it('follows external modelValue changes', async () => {
    const w = mountInput()

    await w.setProps({ modelValue: 'EGFR' })

    expect(state.value.value).toBe('EGFR')
  })

  it.each([
    ['hgnc', { approved_symbol: 'BRCA1', hgnc_id: 'HGNC:1100' }, '✓ Approved symbol: BRCA1'],
    ['pubmed', { title: 'A paper', journal: 'J', pub_date: '2020' }, '✓ Valid PMID'],
    ['hpo', { term_name: 'Hypertension', definition: 'High blood pressure' }, '✓ Hypertension']
  ])('builds a success message for %s', async (validator, data, message) => {
    const w = mountInput({ validator })
    state.result.value = { is_valid: true, data }
    await w.vm.$nextTick()

    // Vuetify 3 has no success-messages prop, so the text is passed through as an attr.
    const field = w.findComponent({ name: 'VTextField' })
    const attrs = field.vm.$attrs as Record<string, unknown>
    expect(attrs.successMessages ?? attrs['success-messages']).toEqual([message])
    expect(document.body.innerHTML).toContain('mdi-check-circle')
  })

  it('shows the error message and icon for an invalid value', async () => {
    const w = mountInput()
    state.result.value = { is_valid: false, error_message: 'Unknown gene' }

    await w.vm.$nextTick()

    expect(w.text()).toContain('Unknown gene')
    expect(document.body.innerHTML).toContain('mdi-alert-circle')
  })

  it('shows the validation error when the request itself failed', async () => {
    const w = mountInput()
    state.error.value = 'Network down'

    await w.vm.$nextTick()

    expect(w.text()).toContain('Network down')
  })

  it('shows a spinner while validating', async () => {
    const w = mountInput()
    state.isValidating.value = true

    await w.vm.$nextTick()

    expect(document.body.innerHTML).toContain('mdi-loading')
  })

  it('offers suggestions and applies one when chosen', async () => {
    const w = mountInput()
    state.result.value = { is_valid: false, suggestions: { did_you_mean: ['BRCA2'] } }
    await w.vm.$nextTick()

    const activator = w.findAll('button').find(b => b.text().includes('Suggestions'))
    activator?.trigger('click')
    await w.vm.$nextTick()

    const suggestion = Array.from(document.querySelectorAll('.v-list-item')).find(item =>
      item.textContent?.includes('BRCA2')
    )
    suggestion?.dispatchEvent(new Event('click', { bubbles: true }))
    await w.vm.$nextTick()

    expect(w.emitted('update:modelValue')?.at(-1)).toEqual(['BRCA2'])
  })
})
