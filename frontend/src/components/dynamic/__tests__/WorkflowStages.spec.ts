/**
 * Tests for WorkflowStages (workflow pipeline and stage actions).
 *
 * The store mock provides the members WorkflowStages calls; the real workflow
 * store does not implement them yet (see WorkflowStages.vue).
 *
 * @see src/components/dynamic/WorkflowStages.vue
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const store = vi.hoisted(() => ({
  loading: false,
  error: null as string | null,
  stages: [] as Array<Record<string, unknown>>,
  current: null as Record<string, unknown> | null,
  history: [] as Array<Record<string, unknown>>,
  getWorkflowStages: vi.fn(),
  getCurrentStage: vi.fn(),
  getStageHistory: vi.fn(),
  advanceStage: vi.fn(),
  rejectStage: vi.fn(),
  requestRevision: vi.fn(),
  saveDraft: vi.fn(),
  fetchWorkflowStages: vi.fn(),
  fetchCurrentStage: vi.fn(),
  fetchStageHistory: vi.fn()
}))

vi.mock('@/stores', () => ({
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
  'v-card-actions': { template: '<div><slot /></div>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-spacer': { template: '<span />' },
  'v-icon': { template: '<span><slot /></span>' },
  'v-chip': { template: '<span><slot /></span>' },
  'v-progress-circular': { template: '<span />' },
  'v-stepper': { template: '<div class="stepper-stub" />' },
  'v-list': { template: '<div><slot /></div>' },
  'v-list-item': { template: '<div><slot /></div>' },
  'v-list-item-title': { template: '<div><slot /></div>' },
  'v-list-item-subtitle': { template: '<div><slot /></div>' },
  'v-expansion-panels': { template: '<div><slot /></div>' },
  'v-expansion-panel': { template: '<div><slot /></div>' },
  'v-expansion-panel-title': { template: '<div><slot /></div>' },
  'v-expansion-panel-text': { template: '<div><slot /></div>' },
  'v-timeline': { template: '<div><slot /></div>' },
  'v-timeline-item': { template: '<div><slot name="icon" /><slot /></div>' },
  'v-alert': { template: '<div><slot name="prepend" /><slot /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' }
}

const stages = [
  { id: 'stage-1', name: 'Draft', stage_type: 'draft', description: 'Start' },
  { id: 'stage-2', name: 'Primary Review', stage_type: 'primary_review', description: 'Review' },
  { id: 'stage-3', name: 'Approved', stage_type: 'approved', description: 'Done' }
]

const currentAt = (stageId: string, overrides: Record<string, unknown> = {}) => ({
  stage_id: stageId,
  name: stages.find(s => s.id === stageId)!.name,
  description: 'Current stage details',
  stage_type: stages.find(s => s.id === stageId)!.stage_type,
  required_roles: ['primary_reviewer'],
  status: 'in_progress',
  validation_rules: [],
  can_advance: false,
  can_reject: false,
  can_request_revision: false,
  ...overrides
})

function mountStages(
  props: Partial<{
    workflowPairId: string
    entityId: string
    entityType: 'precuration' | 'curation'
  }> = {}
) {
  return mount(WorkflowStages, {
    props: {
      workflowPairId: 'pair-1',
      entityId: 'entity-1',
      entityType: 'curation',
      ...props
    },
    global: { stubs }
  })
}

describe('WorkflowStages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.loading = false
    store.error = null
    store.getWorkflowStages.mockImplementation(() => stages)
    store.getCurrentStage.mockImplementation(() => store.current)
    store.getStageHistory.mockImplementation(() => store.history)
    store.current = currentAt('stage-2')
    store.history = []
    store.fetchWorkflowStages.mockResolvedValue(undefined)
    store.fetchCurrentStage.mockResolvedValue(undefined)
    store.fetchStageHistory.mockResolvedValue(undefined)
    store.advanceStage.mockResolvedValue(undefined)
    store.rejectStage.mockResolvedValue(undefined)
    store.requestRevision.mockResolvedValue(undefined)
    store.saveDraft.mockResolvedValue(undefined)
  })

  it('loads stages, current stage and history on mount', async () => {
    mountStages()
    await flushPromises()

    expect(store.fetchWorkflowStages).toHaveBeenCalledWith('pair-1')
    expect(store.fetchCurrentStage).toHaveBeenCalledWith('entity-1', 'curation')
    expect(store.fetchStageHistory).toHaveBeenCalledWith('entity-1')
  })

  it('shows a loading indicator while the store is loading', () => {
    store.loading = true
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Loading workflow stages...')
  })

  it('shows the error when no stages could be loaded', () => {
    store.getWorkflowStages.mockImplementation(() => [])
    store.error = 'Server unavailable'
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Failed to load workflow stages: Server unavailable')
  })

  it('describes the current stage with its position, roles and status', () => {
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Stage 2 of 3')
    expect(wrapper.text()).toContain('Current stage details')
    expect(wrapper.text()).toContain('Primary Reviewer')
    expect(wrapper.text()).toContain('In Progress')
    expect(wrapper.text()).toContain('mdi-account-search')
  })

  it('lists validation rules with their error messages', () => {
    store.current = currentAt('stage-2', {
      validation_rules: [
        { id: 'r1', description: 'Evidence attached', is_satisfied: true },
        {
          id: 'r2',
          description: 'Two reviewers',
          is_satisfied: false,
          error_message: 'Only one reviewer'
        }
      ]
    })
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Validation Requirements')
    expect(wrapper.text()).toContain('Evidence attached')
    expect(wrapper.text()).toContain('Only one reviewer')
  })

  it('offers advancing with the next stage name when allowed', async () => {
    store.current = currentAt('stage-2', { can_advance: true })
    const wrapper = mountStages()

    const advance = wrapper.findAll('button').find(b => b.text().includes('Advance to Approved'))!
    await advance.trigger('click')
    await flushPromises()

    expect(store.advanceStage).toHaveBeenCalledWith({
      entity_id: 'entity-1',
      entity_type: 'curation',
      comment: 'Stage advanced via UI'
    })
    expect(wrapper.emitted('stage-changed')).toEqual([['advanced']])
    expect(wrapper.emitted('action-completed')).toEqual([['advance']])
  })

  it('hides advancing on the last stage', () => {
    store.current = currentAt('stage-3', { can_advance: true })
    const wrapper = mountStages()

    expect(wrapper.findAll('button').some(b => b.text().includes('Advance to'))).toBe(false)
  })

  it('rejects the stage and emits the reject action', async () => {
    store.current = currentAt('stage-2', { can_reject: true })
    const wrapper = mountStages()

    const reject = wrapper.findAll('button').find(b => b.text().includes('Reject'))!
    await reject.trigger('click')
    await flushPromises()

    expect(store.rejectStage).toHaveBeenCalledWith({
      entity_id: 'entity-1',
      entity_type: 'curation',
      comment: 'Stage rejected via UI'
    })
    expect(wrapper.emitted('stage-changed')).toEqual([['rejected']])
    expect(wrapper.emitted('action-completed')).toEqual([['reject']])
  })

  it('requests a revision and emits the revision action', async () => {
    store.current = currentAt('stage-2', { can_request_revision: true })
    const wrapper = mountStages()

    const revision = wrapper.findAll('button').find(b => b.text().includes('Request Revision'))!
    await revision.trigger('click')
    await flushPromises()

    expect(store.requestRevision).toHaveBeenCalledWith({
      entity_id: 'entity-1',
      entity_type: 'curation',
      comment: 'Revision requested via UI'
    })
    expect(wrapper.emitted('stage-changed')).toEqual([['revision_requested']])
    expect(wrapper.emitted('action-completed')).toEqual([['request_revision']])
  })

  it('always offers saving a draft', async () => {
    const wrapper = mountStages()

    const save = wrapper.findAll('button').find(b => b.text().includes('Save Draft'))!
    await save.trigger('click')
    await flushPromises()

    expect(store.saveDraft).toHaveBeenCalledWith({
      entity_id: 'entity-1',
      entity_type: 'curation'
    })
    expect(wrapper.emitted('action-completed')).toEqual([['save_draft']])
  })

  it('keeps the stage unchanged and emits nothing when an action fails', async () => {
    store.current = currentAt('stage-2', { can_advance: true })
    store.advanceStage.mockRejectedValue(new Error('forbidden'))
    const wrapper = mountStages()

    const advance = wrapper.findAll('button').find(b => b.text().includes('Advance to'))!
    await advance.trigger('click')
    await flushPromises()

    expect(wrapper.emitted('stage-changed')).toBeUndefined()
    expect(wrapper.emitted('action-completed')).toBeUndefined()
  })

  it('shows the workflow history with each event', () => {
    store.history = [
      {
        id: 'e1',
        action: 'draft_saved',
        from_stage: 'Draft',
        to_stage: 'Draft',
        created_at: '2026-01-02T10:00:00Z',
        user_name: 'Jane',
        user_role: 'curator',
        comment: 'Initial notes'
      },
      {
        id: 'e2',
        action: 'advanced',
        from_stage: 'Draft',
        to_stage: 'Primary Review',
        created_at: '2026-01-03T10:00:00Z',
        user_name: 'Max',
        user_role: 'reviewer'
      }
    ]
    const wrapper = mountStages()

    expect(wrapper.text()).toContain('Workflow History (2 events)')
    expect(wrapper.text()).toContain('Draft Saved')
    expect(wrapper.text()).toContain('By: Jane (curator)')
    expect(wrapper.text()).toContain('"Initial notes"')
    expect(wrapper.text()).toContain('Stage: Draft → Primary Review')
    expect(wrapper.text()).toContain('mdi-arrow-right-circle')
  })

  it('reloads the stages when the workflow pair changes', async () => {
    const wrapper = mountStages()
    await flushPromises()
    store.fetchWorkflowStages.mockClear()

    await wrapper.setProps({ workflowPairId: 'pair-2' })
    await flushPromises()

    expect(store.fetchWorkflowStages).toHaveBeenCalledWith('pair-2')
  })

  it('reloads the current stage and history when the entity changes', async () => {
    const wrapper = mountStages()
    await flushPromises()
    store.fetchCurrentStage.mockClear()
    store.fetchStageHistory.mockClear()

    await wrapper.setProps({ entityId: 'entity-9' })
    await flushPromises()

    expect(store.fetchCurrentStage).toHaveBeenCalledWith('entity-9', 'curation')
    expect(store.fetchStageHistory).toHaveBeenCalledWith('entity-9')
  })
})
