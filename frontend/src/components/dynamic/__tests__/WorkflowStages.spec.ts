/**
 * Tests for WorkflowStages (workflow pipeline and stage actions).
 *
 * @see src/components/dynamic/WorkflowStages.vue
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const stages = [
  {
    id: 'entry',
    stage_type: 'entry',
    name: 'Entry',
    description: 'Start',
    required_roles: ['curator'],
    order: 1
  },
  {
    id: 'precuration',
    stage_type: 'precuration',
    name: 'Precuration',
    description: 'Gather',
    required_roles: ['curator', 'scope_admin'],
    order: 2
  },
  {
    id: 'curation',
    stage_type: 'curation',
    name: 'Curation',
    description: 'Classify',
    required_roles: ['curator'],
    order: 3
  }
]

const store = vi.hoisted(() => ({
  loading: false,
  error: null as string | null,
  workflowStages: [] as unknown[],
  state: undefined as Record<string, unknown> | undefined,
  history: [] as Array<Record<string, unknown>>,
  getCurrentStage: vi.fn(),
  getStageHistory: vi.fn(),
  advanceStage: vi.fn(),
  rejectStage: vi.fn(),
  fetchCurrentStage: vi.fn(),
  fetchStageHistory: vi.fn()
}))

vi.mock('@/stores/workflow', () => ({
  useWorkflowStore: () => store
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import WorkflowStages from '../WorkflowStages.vue'

const stubs = {
  'v-card': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-spacer': { template: '<span />' },
  'v-icon': { template: '<span><slot /></span>' },
  'v-chip': { template: '<span><slot /></span>' },
  'v-progress-circular': { template: '<span />' },
  'v-stepper': { template: '<div class="stepper-stub" />' },
  'v-expansion-panels': { template: '<div><slot /></div>' },
  'v-expansion-panel': { template: '<div><slot /></div>' },
  'v-expansion-panel-title': { template: '<div><slot /></div>' },
  'v-expansion-panel-text': { template: '<div><slot /></div>' },
  'v-timeline': { template: '<div><slot /></div>' },
  'v-timeline-item': { template: '<div><slot name="icon" /><slot /></div>' },
  'v-alert': { template: '<div><slot name="prepend" /><slot /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' }
}

const stateAt = (current: string, transitions: string[]) => ({
  item_id: 'entity-1',
  item_type: 'curation',
  current_stage: current,
  available_transitions: transitions
})

function mountStages(
  props: Partial<{ entityId: string; entityType: 'precuration' | 'curation' }> = {}
) {
  return mount(WorkflowStages, {
    props: { entityId: 'entity-1', entityType: 'curation', ...props },
    global: { stubs }
  })
}

function buttonWithText(wrapper: ReturnType<typeof mountStages>, text: string) {
  return wrapper.findAll('button').find(b => b.text().includes(text))
}

describe('WorkflowStages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.loading = false
    store.error = null
    store.workflowStages = stages
    store.state = stateAt('precuration', ['entry', 'curation'])
    store.history = []
    store.getCurrentStage.mockImplementation(() => store.state)
    store.getStageHistory.mockImplementation(() => store.history)
    store.fetchCurrentStage.mockResolvedValue(undefined)
    store.fetchStageHistory.mockResolvedValue(undefined)
    store.advanceStage.mockResolvedValue(undefined)
    store.rejectStage.mockResolvedValue(undefined)
  })

  it('loads the current stage and history for the entity on mount', async () => {
    mountStages()
    await flushPromises()

    expect(store.fetchCurrentStage).toHaveBeenCalledWith('entity-1', 'curation')
    expect(store.fetchStageHistory).toHaveBeenCalledWith('entity-1', 'curation')
  })

  it('reloads when the entity changes', async () => {
    const wrapper = mountStages()
    await flushPromises()

    await wrapper.setProps({ entityId: 'entity-2' })
    await flushPromises()

    expect(store.fetchCurrentStage).toHaveBeenLastCalledWith('entity-2', 'curation')
    expect(store.fetchStageHistory).toHaveBeenLastCalledWith('entity-2', 'curation')
  })

  it('logs a failed load without throwing', async () => {
    store.fetchCurrentStage.mockRejectedValue(new Error('offline'))

    const wrapper = mountStages()
    await flushPromises()

    expect(wrapper.exists()).toBe(true)
  })

  it('shows a loading indicator while the store is loading', () => {
    store.loading = true
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Loading workflow stages...')
  })

  it('shows the error when no stages are available', () => {
    store.workflowStages = []
    store.error = 'Boom'
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Failed to load workflow stages: Boom')
  })

  it('describes the current stage with its position and required roles', () => {
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Precuration')
    expect(wrapper.text()).toContain('Stage 2 of 3')
    expect(wrapper.text()).toContain('Gather')
    expect(wrapper.text()).toContain('Scope Admin')
  })

  it('offers advancing with the next stage name and returning, from the backend transitions', () => {
    const wrapper = mountStages()

    expect(buttonWithText(wrapper, 'Advance to Curation')).toBeDefined()
    expect(buttonWithText(wrapper, 'Reject & Return')).toBeDefined()
  })

  it('hides actions the backend does not allow and has no draft or revision actions', () => {
    store.state = stateAt('entry', [])
    const wrapper = mountStages()

    expect(buttonWithText(wrapper, 'Advance')).toBeUndefined()
    expect(buttonWithText(wrapper, 'Reject')).toBeUndefined()
    expect(buttonWithText(wrapper, 'Save Draft')).toBeUndefined()
    expect(buttonWithText(wrapper, 'Request Revision')).toBeUndefined()
  })

  it('advances the stage and emits the advance events', async () => {
    const wrapper = mountStages()

    await buttonWithText(wrapper, 'Advance to Curation')!.trigger('click')
    await flushPromises()

    expect(store.advanceStage).toHaveBeenCalledWith({
      entity_id: 'entity-1',
      entity_type: 'curation',
      comment: 'Stage advanced via UI'
    })
    expect(wrapper.emitted('stage-changed')![0]).toEqual(['advanced'])
    expect(wrapper.emitted('action-completed')![0]).toEqual(['advance'])
  })

  it('rejects the stage and emits the reject events', async () => {
    const wrapper = mountStages({ entityType: 'precuration' })

    await buttonWithText(wrapper, 'Reject & Return')!.trigger('click')
    await flushPromises()

    expect(store.rejectStage).toHaveBeenCalledWith({
      entity_id: 'entity-1',
      entity_type: 'precuration',
      comment: 'Stage rejected via UI'
    })
    expect(wrapper.emitted('stage-changed')![0]).toEqual(['rejected'])
    expect(wrapper.emitted('action-completed')![0]).toEqual(['reject'])
  })

  it('emits nothing when an action fails', async () => {
    store.advanceStage.mockRejectedValue(new Error('no transition'))
    store.rejectStage.mockRejectedValue(new Error('no transition'))
    const wrapper = mountStages()

    await buttonWithText(wrapper, 'Advance to Curation')!.trigger('click')
    await buttonWithText(wrapper, 'Reject & Return')!.trigger('click')
    await flushPromises()

    expect(wrapper.emitted('stage-changed')).toBeUndefined()
    expect(wrapper.emitted('action-completed')).toBeUndefined()
  })

  it('shows the workflow history with forward and backward transitions', () => {
    store.history = [
      {
        id: 'h1',
        from_stage: null,
        to_stage: 'entry',
        executed_at: '2026-01-01T10:00:00Z',
        notes: null
      },
      {
        id: 'h2',
        from_stage: 'precuration',
        to_stage: 'curation',
        executed_at: '2026-01-02T10:00:00Z',
        notes: 'Looks good'
      },
      {
        id: 'h3',
        from_stage: 'curation',
        to_stage: 'precuration',
        executed_at: '2026-01-03T10:00:00Z',
        notes: null
      }
    ]
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Workflow History (3 events)')
    expect(wrapper.text()).toContain('none → entry')
    expect(wrapper.text()).toContain('"Looks good"')
    expect(wrapper.text()).toContain('Returned')
    expect(wrapper.text()).toContain('Advanced')
  })
})
