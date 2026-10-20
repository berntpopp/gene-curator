/**
 * Behaviour tests for ValidationDashboard and its helpers.
 * The summary figures are derived from the validation store's results (no statistics endpoint).
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { call, vmOf } from './vm'
import ValidationDashboard from '@/views/ValidationDashboard.vue'
import {
  getValidationStatusColor,
  getValidationStatusIcon,
  getSeverityColor,
  formatValidationStatus
} from '@/views/validationDashboardHelpers'
import { useValidationStore } from '@/stores/validation'

let pinia: ReturnType<typeof createPinia>

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  document.body.innerHTML = ''
})

const response = (overrides: Record<string, unknown>) => ({
  is_valid: true,
  errors: [],
  warnings: [],
  field_validations: {},
  business_rule_violations: [],
  score_calculations: {},
  completeness_score: 1,
  required_fields_missing: [],
  suggested_improvements: [],
  ...overrides
})

const mountView = async () => {
  const validation = useValidationStore()
  validation.validationResults = {
    r1: response({}),
    r2: response({ is_valid: false, errors: [{ message: 'Gene not found', field: 'gene' }] }),
    r3: response({ is_valid: false, errors: [{ error: 'Gene not found' }] }),
    r4: response({ warnings: [{ code: 'odd' }] })
  } as never
  const wrapper = mount(ValidationDashboard, {
    attachTo: document.body,
    global: { plugins: [pinia] }
  })
  await flushPromises()
  return { wrapper, vm: vmOf(wrapper) }
}

describe('ValidationDashboard', () => {
  it('derives the summary cards and common issues from the stored results', async () => {
    const { wrapper } = await mountView()
    const text = wrapper.text().replace(/\s+/g, ' ')
    expect(text).toContain('2Valid')
    expect(text).toContain('2Invalid')
    expect(text).toContain('1With warnings')
    expect(text).toContain('50%Compliance Rate')
    expect(text).toContain('Gene not found')
    expect(text).toContain('2 occurrences')
    expect(text).toContain('{"code":"odd"}')
  })

  it('renders an empty dashboard when nothing has been validated', async () => {
    const wrapper = mount(ValidationDashboard, { global: { plugins: [pinia] } })
    await flushPromises()
    expect(wrapper.text().replace(/\s+/g, ' ')).toContain('0%Compliance Rate')
    expect(wrapper.text()).toContain('Validation Results (0)')
  })

  it('does not offer scope/schema filters or re-validation (no data behind them)', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).not.toContain('Filter by Scope')
    expect(wrapper.text()).not.toContain('Refresh All')
  })

  it('filters by status and by issue severity', async () => {
    const { vm } = await mountView()
    const rows = () => (vm.filteredResults as unknown[]).length
    expect(rows()).toBe(4)
    vm.selectedStatus = 'valid'
    await nextTick()
    expect(rows()).toBe(2)
    vm.selectedStatus = null
    vm.selectedSeverity = 'warning'
    await nextTick()
    expect(rows()).toBe(1)
    vm.selectedSeverity = 'error'
    await nextTick()
    expect(rows()).toBe(2)
  })

  it('shows the issues of a result, or a success message when it has none', async () => {
    const { vm } = await mountView()
    const results = vm.validationResults as { id: string }[]
    call(
      vm,
      'viewValidationDetails',
      results.find(r => r.id === 'r2')
    )
    await nextTick()
    expect(vm.detailDialog).toBe(true)
    expect(document.body.textContent).toContain('Gene not found')
    expect(document.body.textContent).toContain('Field: gene')
    call(
      vm,
      'viewValidationDetails',
      results.find(r => r.id === 'r1')
    )
    await nextTick()
    expect(document.body.textContent).toContain('No Issues Found')
  })
})

describe('validationDashboardHelpers', () => {
  it('maps statuses and severities to colours and icons with a grey fallback', () => {
    expect(getValidationStatusColor('valid')).toBe('success')
    expect(getValidationStatusColor('zzz')).toBe('grey')
    expect(getValidationStatusIcon('invalid')).toBe('mdi-close')
    expect(getValidationStatusIcon('zzz')).toBe('mdi-help')
    expect(getSeverityColor('warning')).toBe('warning')
    expect(getSeverityColor('zzz')).toBe('grey')
    expect(formatValidationStatus('pending')).toBe('Pending')
  })
})
