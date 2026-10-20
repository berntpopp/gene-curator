import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AssignmentDetail from '@/views/AssignmentDetail.vue'
import { useAssignmentsStore } from '@/stores/assignments'
import { call, vmOf } from './vm'

const { routeState, logger } = vi.hoisted(() => ({
  routeState: { params: { id: 'a1' } as Record<string, string>, query: {} },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
  useRouter: () => ({ push: vi.fn(), back: vi.fn() })
}))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const assignment = {
  id: 'a1',
  workflow_pair_id: 'wp1',
  status: 'in_progress',
  gene_symbol: 'HNF1B',
  gene_name: 'HNF1 homeobox B',
  disease_name: 'Renal cysts',
  omim_id: '137920',
  scope_display_name: 'Kidney',
  workflow_pair_name: 'ClinGen flow',
  assigned_to: 'u1',
  assignee_name: 'Ada',
  due_date: '2999-01-01',
  notes: 'Prioritise',
  precuration_schema_id: 'pre',
  curation_schema_id: 'cur',
  current_stage: 'curation',
  precuration_data: { a: 1 },
  curation_data: { b: 2 }
}

// The assignments store has none of these methods yet; tests provide fakes.
const fakeStore = (overrides: Record<string, unknown> = {}) => {
  const store = useAssignmentsStore()
  const fakes = {
    fetchAssignmentById: vi.fn(async () => assignment),
    fetchAssignmentHistory: vi.fn(async () => [
      {
        id: 'e1',
        event_type: 'precuration_submitted',
        description: 'Submitted',
        created_at: '2026-01-01T00:00:00Z',
        user_name: 'Ada',
        user_role: 'curator',
        details: 'All good'
      }
    ]),
    submitPrecuration: vi.fn(async () => undefined),
    savePrecurationDraft: vi.fn(async () => undefined),
    submitCuration: vi.fn(async () => undefined),
    saveCurationDraft: vi.fn(async () => undefined),
    ...overrides
  }
  Object.assign(store, fakes)
  return fakes
}

const mountView = async (overrides: Record<string, unknown> = {}) => {
  const fakes = fakeStore(overrides)
  const wrapper = mount(AssignmentDetail, {
    global: { stubs: { DynamicForm: true, ScoreDisplay: true } }
  })
  await flushPromises()
  return { wrapper, fakes, vm: vmOf(wrapper) }
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
  routeState.params = { id: 'a1' }
})

describe('AssignmentDetail', () => {
  it('shows the assignment overview and its history', async () => {
    const { wrapper, fakes } = await mountView()
    expect(fakes.fetchAssignmentById).toHaveBeenCalledWith('a1')
    const text = wrapper.text()
    expect(text).toContain('HNF1B - Renal cysts')
    expect(text).toContain('Kidney • ClinGen flow')
    expect(text).toContain('In Progress')
    expect(text).toContain('Ada')
    expect(text).toContain('Prioritise')
  })

  it('does not render the workflow stage widget (assignments have no workflow)', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.findComponent({ name: 'WorkflowStages' }).exists()).toBe(false)
  })

  it('shows unassigned and no due date when absent', async () => {
    const { wrapper } = await mountView({
      fetchAssignmentById: vi.fn(async () => ({
        ...assignment,
        assigned_to: null,
        due_date: null,
        notes: null
      }))
    })
    expect(wrapper.text()).toContain('Unassigned')
    expect(wrapper.text()).toContain('No due date')
  })

  it('shows the error state when loading fails', async () => {
    const { wrapper } = await mountView({
      fetchAssignmentById: vi.fn(async () => {
        throw new Error('Not found')
      })
    })
    expect(wrapper.text()).toContain('Failed to load assignment: Not found')
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to load assignment:',
      expect.objectContaining({ error: 'Not found' })
    )
  })

  it('submits precuration data and switches to curation when it is accessible', async () => {
    const { fakes, vm } = await mountView()
    await call(vm, 'handlePrecurationSubmit', { x: 1 })
    expect(fakes.submitPrecuration).toHaveBeenCalledWith('a1', { x: 1 })
    expect(vm.precurationData).toEqual({ x: 1 })
    expect(vm.activeTab).toBe('curation')
  })

  it('saves drafts and submits curation, moving on to scoring', async () => {
    const { fakes, vm } = await mountView()
    await call(vm, 'handlePrecurationDraft', { p: 1 })
    await call(vm, 'handleCurationDraft', { c: 1 })
    expect(fakes.savePrecurationDraft).toHaveBeenCalledWith('a1', { p: 1 })
    expect(fakes.saveCurationDraft).toHaveBeenCalledWith('a1', { c: 1 })
    await call(vm, 'handleCurationSubmit', { c: 2 })
    expect(fakes.submitCuration).toHaveBeenCalledWith('a1', { c: 2 })
    expect(vm.activeTab).toBe('scoring')
    expect(vm.combinedEvidenceData).toEqual({ p: 1, c: 2 })
  })

  it('logs failed saves without throwing', async () => {
    const boom = vi.fn(async () => {
      throw new Error('boom')
    })
    const { vm } = await mountView({
      submitPrecuration: boom,
      savePrecurationDraft: boom,
      submitCuration: boom,
      saveCurationDraft: boom
    })
    await call(vm, 'handlePrecurationSubmit', {})
    await call(vm, 'handlePrecurationDraft', {})
    await call(vm, 'handleCurationSubmit', {})
    await call(vm, 'handleCurationDraft', {})
    expect(logger.error).toHaveBeenCalledTimes(4)
  })

  it('uses the schema of the active tab for scoring', async () => {
    const { vm } = await mountView()
    expect(vm.currentScoringSchemaId).toBe('pre')
    vm.activeTab = 'curation'
    expect(vm.currentScoringSchemaId).toBe('cur')
  })

  it('blocks curation until precuration is complete', async () => {
    const { vm } = await mountView({
      fetchAssignmentById: vi.fn(async () => ({
        ...assignment,
        current_stage: 'precuration',
        precuration_status: 'draft'
      }))
    })
    expect(vm.canAccessCuration).toBe(false)
  })

  it('formats statuses, dates, due-date urgency and history events', async () => {
    const { vm } = await mountView()
    expect(call(vm, 'formatStatus', 'pending_review')).toBe('Pending Review')
    expect(call(vm, 'getStatusColor', 'completed')).toBe('success')
    expect(call(vm, 'getStatusColor', 'zzz')).toBe('grey')
    expect(call(vm, 'formatEventType', 'review_requested')).toBe('Review Requested')
    expect(call(vm, 'getEventColor', 'approved')).toBe('success')
    expect(call(vm, 'getEventColor', 'zzz')).toBe('grey')
    expect(call(vm, 'getEventIcon', 'rejected')).toBe('mdi-close-circle')
    expect(call(vm, 'getEventIcon', 'zzz')).toBe('mdi-circle')
    const day = 24 * 60 * 60 * 1000
    const iso = (offset: number) => new Date(Date.now() + offset * day).toISOString()
    expect(call(vm, 'getDueDateClass', iso(-2))).toBe('text-error')
    expect(call(vm, 'getDueDateClass', iso(3))).toBe('text-warning')
    expect(call(vm, 'getDueDateClass', iso(30))).toBe('text-success')
    expect(call(vm, 'formatDate', '2026-01-02T00:00:00Z')).not.toBe('')
    expect(call(vm, 'formatDateTime', '2026-01-02T00:00:00Z')).not.toBe('')
  })

  it('logs score and classification updates', async () => {
    const { vm } = await mountView()
    call(vm, 'handleScoreUpdated', { total: 3 })
    call(vm, 'handleClassificationChanged', { value: 'Strong' })
    expect(logger.info).toHaveBeenCalledWith('Scores updated:', { total: 3 })
    expect(logger.info).toHaveBeenCalledWith('Classification changed:', { value: 'Strong' })
  })
})
