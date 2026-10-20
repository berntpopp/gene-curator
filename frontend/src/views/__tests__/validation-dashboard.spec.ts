/**
 * Behaviour tests for ValidationDashboard and its helpers.
 * Stores are real Pinia stores; their actions are stubbed with vi.spyOn.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import './visualViewport'
import ValidationDashboard from '@/views/ValidationDashboard.vue'
import {
  getValidationStatusColor,
  getValidationStatusIcon,
  getSeverityColor,
  formatValidationStatus,
  formatDate,
  getTimeAgo
} from '@/views/validationDashboardHelpers'
import { useSchemasStore } from '@/stores/schemas'
import { useScopesStore } from '@/stores/scopes'
import { useValidationStore } from '@/stores/validation'

const { routerPush, routeState, logger, showError, showSuccess, showInfo } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routeState: { params: {} as Record<string, string>, query: {} as Record<string, string> },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showInfo: vi.fn()
}))

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: routerPush, back: vi.fn() }),
  useRoute: () => routeState
}))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/composables/useNotifications', () => ({
  showError,
  showSuccess,
  showInfo,
  showWarning: vi.fn()
}))

let pinia: ReturnType<typeof createPinia>
const opts = () => ({
  attachTo: document.body,
  global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
})

beforeEach(() => {
  vi.clearAllMocks()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  document.body.innerHTML = ''
})

type Vm = Record<string, unknown> & Record<string, (...args: never[]) => Promise<void> | void>
const vmOf = (wrapper: { vm: unknown }) => wrapper.vm as unknown as Vm

describe('ValidationDashboard', () => {
  const mountView = async () => {
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue(undefined as never)
    vi.spyOn(useSchemasStore(), 'fetchSchemas').mockResolvedValue(undefined as never)
    const validation = useValidationStore()
    validation.validationResults = {
      r1: { is_valid: true, status: 'valid' },
      r2: { is_valid: false, status: 'invalid', error_message: 'Gene not found' },
      r3: { is_valid: false, status: 'error', error_message: 'Gene not found' },
      r4: {
        is_valid: false,
        status: 'warning',
        issues: [{ id: 'w', message: 'Odd', severity: 'warning' }],
        evidence_data: { a: 1 },
        schema_id: 'sch1',
        entity_id: 'e4',
        scope_id: 'sc1'
      }
    } as never
    const wrapper = mount(ValidationDashboard, opts())
    await flushPromises()
    return { wrapper, validation, vm: vmOf(wrapper) }
  }

  it('derives the summary cards and common issues from the stored results', async () => {
    const { wrapper } = await mountView()
    const text = wrapper.text().replace(/\s+/g, ' ')
    expect(text).toContain('1Valid Curations')
    expect(text).toContain('1Invalid Curations')
    expect(text).toContain('1Warnings')
    expect(text).toContain('25% Compliance Rate')
    expect(text).toContain('Gene not found')
    expect(text).toContain('2 occurrences')
  })

  it('loads the filter lists through existing store actions without errors', async () => {
    await mountView()
    expect(showError).not.toHaveBeenCalled()
    expect(logger.info).toHaveBeenCalledWith('ValidationDashboard mounted', expect.anything())
  })

  it('reports a failed load', async () => {
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockRejectedValue(new Error('down'))
    vi.spyOn(useSchemasStore(), 'fetchSchemas').mockResolvedValue(undefined as never)
    mount(ValidationDashboard, opts())
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Failed to load dashboard data. Please refresh.')
  })

  it('filters by status, scope, schema and severity', async () => {
    const { vm } = await mountView()
    const rows = () => (vm.filteredResults as unknown as unknown[]).length
    expect(rows()).toBe(4)
    vm.selectedStatus = 'valid'
    await nextTick()
    expect(rows()).toBe(1)
    vm.selectedStatus = null
    vm.selectedScope = 'sc1'
    await nextTick()
    expect(rows()).toBe(1)
    vm.selectedScope = null
    vm.selectedSchema = 'sch1'
    await nextTick()
    expect(rows()).toBe(1)
    vm.selectedSchema = null
    vm.selectedSeverity = 'error'
    await nextTick()
    expect(rows()).toBe(2)
  })

  it('revalidates a row through the validation store', async () => {
    const { vm, validation } = await mountView()
    const validate = vi
      .spyOn(validation, 'validateEvidence')
      .mockResolvedValue({ is_valid: true, status: 'valid' } as never)
    const row = { id: 'r4', evidence_data: { a: 1 }, schema_id: 'sch1', entity_id: 'e4' }
    await (vm.revalidateEntity as (r: unknown) => Promise<void>)(row)
    expect(validate).toHaveBeenCalledWith({ a: 1 }, 'sch1', 'r4')
    expect(showSuccess).toHaveBeenCalledWith('Revalidation complete')
    validate.mockRejectedValueOnce(new Error('x'))
    await (vm.revalidateEntity as (r: unknown) => Promise<void>)(row)
    expect(showError).toHaveBeenCalledWith('Revalidation failed')
  })

  it('does not revalidate a row without evidence data or schema', async () => {
    const { vm, validation } = await mountView()
    const validate = vi.spyOn(validation, 'validateEvidence').mockResolvedValue(undefined as never)
    await (vm.revalidateEntity as (r: unknown) => Promise<void>)({ id: 'r1' })
    expect(validate).not.toHaveBeenCalled()
    expect(showError).toHaveBeenCalledWith(
      'Nothing to re-validate: evidence data or schema is missing'
    )
  })

  it('refreshes the filter lists and reports the outcome', async () => {
    const { vm } = await mountView()
    await vm.refreshAll()
    expect(showSuccess).toHaveBeenCalledWith('Dashboard refreshed successfully')
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockRejectedValue(new Error('x'))
    await vm.refreshAll()
    expect(showError).toHaveBeenCalledWith('Failed to refresh dashboard')
  })

  it('shows row details and navigates to the entity', async () => {
    const { vm } = await mountView()
    const row = { id: 'r4', entity_id: 'e4', issues: [], validation_status: 'valid' }
    ;(vm.viewValidationDetails as (r: unknown) => void)(row)
    await nextTick()
    expect(vm.detailDialog).toBe(true)
    expect(document.body.textContent).toContain('No Issues Found')
    ;(vm.viewEntity as (r: unknown) => void)(row)
    expect(routerPush).toHaveBeenCalledWith({ name: 'AssignmentDetail', params: { id: 'e4' } })
    routerPush.mockImplementationOnce(() => {
      throw new Error('nav')
    })
    ;(vm.viewEntity as (r: unknown) => void)(row)
    expect(showError).toHaveBeenCalledWith('Failed to open entity details')
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

  it('formats dates and relative times', () => {
    const now = new Date('2026-03-10T12:00:00Z')
    expect(formatDate(null)).toBe('N/A')
    expect(formatDate('2026-03-10T12:00:00Z')).not.toBe('N/A')
    expect(getTimeAgo(null)).toBe('')
    expect(getTimeAgo('2026-03-10T11:30:00Z', now)).toBe('Just now')
    expect(getTimeAgo('2026-03-10T07:00:00Z', now)).toBe('5h ago')
    expect(getTimeAgo('2026-03-07T12:00:00Z', now)).toBe('3d ago')
    expect(getTimeAgo('2026-02-01T12:00:00Z', now)).toBe('Over a week ago')
  })
})
