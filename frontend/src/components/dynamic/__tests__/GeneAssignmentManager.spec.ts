/**
 * Tests for GeneAssignmentManager (assignment table, filters and dialogs).
 *
 * @see src/components/dynamic/GeneAssignmentManager.vue
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'

const stores = vi.hoisted(() => ({
  assignments: {
    loading: false,
    assignments: [] as Array<Record<string, unknown>>,
    fetchAssignments: vi.fn(),
    updateAssignment: vi.fn(),
    fetchCuratorWorkload: vi.fn()
  },
  scopes: { scopes: [] as Array<Record<string, unknown>>, fetchUserScopes: vi.fn() },
  users: { users: [] as Array<Record<string, unknown>>, fetchUsers: vi.fn() },
  auth: { user: { id: 'curator-1' } as { id: string } | null }
}))

const api = vi.hoisted(() => ({
  assignCurator: vi.fn(),
  updateAssignment: vi.fn()
}))

const notify = vi.hoisted(() => ({
  showError: vi.fn(),
  showSuccess: vi.fn()
}))

vi.mock('@/stores', () => ({
  useAssignmentsStore: () => stores.assignments,
  useScopesStore: () => stores.scopes,
  useUsersStore: () => stores.users,
  useAuthStore: () => stores.auth
}))

vi.mock('@/api', () => ({
  assignmentsAPI: api
}))

vi.mock('@/composables/useNotifications', () => notify)

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import GeneAssignmentManager from '../GeneAssignmentManager.vue'

/** Renders every item slot the table defines, so row helpers are exercised */
const stubs = {
  'v-card': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-card-actions': { template: '<div><slot /></div>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-spacer': { template: '<span />' },
  'v-icon': { template: '<span />' },
  'v-chip': { template: '<span><slot /></span>' },
  'v-avatar': { template: '<span><slot /></span>' },
  'v-toolbar': { template: '<div><slot /></div>' },
  'v-dialog': { template: '<div><slot /></div>' },
  'v-form': {
    template: '<form><slot /></form>',
    methods: { validate: () => Promise.resolve({ valid: true }) }
  },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' },
  'v-list': { template: '<div><slot /></div>' },
  'v-list-item': { template: '<div><slot /></div>' },
  'v-list-item-title': { template: '<div><slot /></div>' },
  'v-list-item-subtitle': { template: '<div><slot /></div>' },
  'v-select': {
    name: 'VSelect',
    props: ['items', 'modelValue', 'label'],
    template: '<div class="v-select-stub" />'
  },
  'v-text-field': {
    name: 'VTextField',
    props: ['modelValue', 'label'],
    template: '<div class="v-text-field-stub" />'
  },
  'v-textarea': {
    name: 'VTextarea',
    props: ['modelValue', 'label'],
    template: '<div class="v-textarea-stub" />'
  },
  'v-data-table': {
    name: 'VDataTable',
    props: ['items', 'modelValue'],
    template: `<div>
      <div v-for="item in items" :key="item.id" class="row-stub">
        <slot name="item.gene_symbol" :item="item" />
        <slot name="item.scope_name" :item="item" />
        <slot name="item.curator_name" :item="item" />
        <slot name="item.priority" :item="item" />
        <slot name="item.actions" :item="item" />
      </div>
    </div>`
  }
}

const scopeA = { id: 'scope-a', display_name: 'Cancer', is_active: true }
const scopeB = { id: 'scope-b', display_name: 'Metabolic', is_active: true }
const curatorUser = { id: 'curator-1', name: 'Ada Curator', role: 'user', is_active: true }
const reviewerUser = { id: 'reviewer-1', name: 'Rex Reviewer', role: 'user', is_active: true }
const inactiveUser = { id: 'gone-1', name: 'Gone Away', role: 'user', is_active: false }

const assignmentOne = {
  id: 'a1',
  gene_id: 'g1',
  gene_symbol: 'HNF1B',
  gene_hgnc_id: 'HGNC:11630',
  scope_id: 'scope-a',
  scope_name: 'Cancer',
  assigned_curator_id: 'curator-1',
  curator_name: 'Ada Curator',
  priority: 'high',
  is_active: true,
  assigned_at: '2026-01-01T00:00:00Z',
  has_active_work: false
}

const assignmentTwo = {
  id: 'a2',
  gene_id: 'g2',
  gene_symbol: 'PKD1',
  gene_hgnc_id: 'HGNC:9008',
  scope_id: 'scope-b',
  scope_name: 'Metabolic',
  assigned_curator_id: null,
  curator_name: null,
  priority: 'low',
  is_active: true,
  assigned_at: '2026-01-02T00:00:00Z',
  has_active_work: false
}

/** Finds a form control stub by its label prop */
function byLabel(wrapper: VueWrapper, label: string) {
  const control = wrapper
    .findAllComponents({ name: 'VSelect' })
    .concat(wrapper.findAllComponents({ name: 'VTextField' }))
    .concat(wrapper.findAllComponents({ name: 'VTextarea' }))
    .find(c => c.props('label') === label)
  if (!control) throw new Error(`No control labelled ${label}`)
  return control
}

function buttonWithText(wrapper: VueWrapper, text: string) {
  const button = wrapper.findAll('button').find(b => b.text().trim() === text)
  if (!button) throw new Error(`No button containing ${text}`)
  return button
}

function mountManager() {
  return mount(GeneAssignmentManager, { global: { stubs } })
}

describe('GeneAssignmentManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    stores.assignments.assignments = [assignmentOne, assignmentTwo] as never
    stores.scopes.scopes = [scopeA, scopeB]
    stores.users.users = [curatorUser, reviewerUser, inactiveUser]
    stores.auth.user = { id: 'curator-1' }
    stores.assignments.fetchAssignments.mockResolvedValue(undefined)
    stores.assignments.fetchCuratorWorkload.mockResolvedValue(undefined)
    api.updateAssignment.mockResolvedValue(undefined)
    stores.assignments.updateAssignment.mockResolvedValue(undefined)
    stores.scopes.fetchUserScopes.mockResolvedValue(undefined)
    stores.users.fetchUsers.mockResolvedValue(undefined)
    api.assignCurator.mockResolvedValue(undefined)
  })

  describe('loading', () => {
    it('loads assignments, scopes, users and the curator workload on mount', async () => {
      mountManager()
      await flushPromises()

      expect(stores.assignments.fetchAssignments).toHaveBeenCalledTimes(1)
      expect(stores.scopes.fetchUserScopes).toHaveBeenCalledTimes(1)
      expect(stores.users.fetchUsers).toHaveBeenCalledTimes(1)
      expect(stores.assignments.fetchCuratorWorkload).toHaveBeenCalledWith('curator-1')
    })

    it('skips the workload fetch when no user is logged in', async () => {
      stores.auth.user = null
      mountManager()
      await flushPromises()

      expect(stores.assignments.fetchCuratorWorkload).not.toHaveBeenCalled()
    })

    it('reports a failed initial load', async () => {
      stores.assignments.fetchAssignments.mockRejectedValue(new Error('offline'))
      mountManager()
      await flushPromises()

      expect(notify.showError).toHaveBeenCalledWith(
        'Failed to load assignment data. Please refresh.'
      )
    })
  })

  describe('table', () => {
    it('renders each row with scope, assignee and priority', () => {
      const wrapper = mountManager()
      const rows = wrapper.findAll('.row-stub')

      expect(rows).toHaveLength(2)
      expect(rows[0]!.text()).toContain('HNF1B')
      expect(rows[0]!.text()).toContain('HGNC:11630')
      expect(rows[0]!.text()).toContain('Cancer')
      expect(rows[0]!.text()).toContain('Ada Curator')
      expect(rows[0]!.text()).toContain('High')
      expect(rows[1]!.text()).toContain('Unassigned')
      expect(rows[1]!.text()).toContain('Metabolic')
    })

    it('offers only active users as assignees', () => {
      const wrapper = mountManager()

      const items = byLabel(wrapper, 'Filter by Assignee').props('items') as { id: string }[]
      expect(items.map(u => u.id)).toEqual(['curator-1', 'reviewer-1'])
    })

    it('has no status filter (the API carries no assignment status)', () => {
      const wrapper = mountManager()

      expect(() => byLabel(wrapper, 'Filter by Status')).toThrow()
    })

    it('filters rows by scope and assignee', async () => {
      const wrapper = mountManager()
      const table = () => wrapper.findComponent({ name: 'VDataTable' })

      byLabel(wrapper, 'Filter by Scope').vm.$emit('update:model-value', 'scope-b')
      await flushPromises()
      expect(table().props('items')).toEqual([assignmentTwo])

      byLabel(wrapper, 'Filter by Scope').vm.$emit('update:model-value', null)
      byLabel(wrapper, 'Filter by Assignee').vm.$emit('update:model-value', 'curator-1')
      await flushPromises()
      expect(table().props('items')).toEqual([assignmentOne])
    })

    it('refreshes the assignments and confirms', async () => {
      const wrapper = mountManager()
      await flushPromises()
      stores.assignments.fetchAssignments.mockClear()

      await buttonWithText(wrapper, 'Refresh').trigger('click')
      await flushPromises()

      expect(stores.assignments.fetchAssignments).toHaveBeenCalledTimes(1)
      expect(notify.showSuccess).toHaveBeenCalledWith('Assignments refreshed')
    })

    it('reports a failed refresh', async () => {
      const wrapper = mountManager()
      await flushPromises()
      stores.assignments.fetchAssignments.mockRejectedValue(new Error('timeout'))

      await buttonWithText(wrapper, 'Refresh').trigger('click')
      await flushPromises()

      expect(notify.showError).toHaveBeenCalledWith('Refresh failed')
    })
  })

  describe('bulk assignment', () => {
    it('is disabled until rows are selected', () => {
      const wrapper = mountManager()

      expect(buttonWithText(wrapper, 'Bulk Assign (0)').attributes('disabled')).toBeDefined()
    })

    it('assigns the selected rows to the chosen user', async () => {
      const wrapper = mountManager()
      wrapper.findComponent({ name: 'VDataTable' }).vm.$emit('update:model-value', ['a1', 'a2'])
      await flushPromises()

      await buttonWithText(wrapper, 'Bulk Assign (2)').trigger('click')
      byLabel(wrapper, 'Assign to User').vm.$emit('update:model-value', curatorUser)
      byLabel(wrapper, 'Set Priority').vm.$emit('update:model-value', 'high')
      await flushPromises()

      await buttonWithText(wrapper, 'Assign').trigger('click')
      await flushPromises()

      expect(api.assignCurator).toHaveBeenCalledTimes(2)
      expect(api.assignCurator).toHaveBeenCalledWith('a1', 'curator-1')
      expect(api.assignCurator).toHaveBeenCalledWith('a2', 'curator-1')
      expect(api.updateAssignment).toHaveBeenCalledWith('a2', {
        priority_level: 'high'
      })
      expect(notify.showSuccess).toHaveBeenCalledWith('Successfully assigned 2 items')
    })

    it('does nothing without a chosen user', async () => {
      const wrapper = mountManager()
      wrapper.findComponent({ name: 'VDataTable' }).vm.$emit('update:model-value', ['a1'])
      await flushPromises()

      await buttonWithText(wrapper, 'Assign').trigger('click')
      await flushPromises()

      expect(api.assignCurator).not.toHaveBeenCalled()
    })

    it('reports a failed bulk assignment', async () => {
      api.assignCurator.mockRejectedValue(new Error('conflict'))
      const wrapper = mountManager()
      wrapper.findComponent({ name: 'VDataTable' }).vm.$emit('update:model-value', ['a1'])
      await flushPromises()
      await buttonWithText(wrapper, 'Bulk Assign (1)').trigger('click')
      byLabel(wrapper, 'Assign to User').vm.$emit('update:model-value', curatorUser)
      await flushPromises()

      await buttonWithText(wrapper, 'Assign').trigger('click')
      await flushPromises()

      expect(notify.showError).toHaveBeenCalledWith('Bulk assignment failed')
    })
  })

  describe('row actions', () => {
    it('shows the details of an assignment', async () => {
      const wrapper = mountManager()

      const viewButton = wrapper.findAll('.row-stub')[1]!.findAll('button')[2]!
      await viewButton.trigger('click')

      expect(wrapper.text()).toContain('Assignment Details')
      expect(wrapper.text()).toContain('PKD1')
      expect(wrapper.text()).toContain('Unassigned')
      expect(wrapper.text()).toContain('HGNC:9008')
    })

    it('edits priority and notes, then saves only what was filled', async () => {
      const wrapper = mountManager()

      await wrapper.findAll('.row-stub')[0]!.findAll('button')[0]!.trigger('click')
      expect(byLabel(wrapper, 'Priority').props('modelValue')).toBe('high')
      expect(() => byLabel(wrapper, 'Due Date')).toThrow()

      await buttonWithText(wrapper, 'Save').trigger('click')
      await flushPromises()
      expect(stores.assignments.updateAssignment).toHaveBeenCalledWith('a1', {
        priority_level: 'high'
      })

      byLabel(wrapper, 'Notes').vm.$emit('update:model-value', 'Check literature')
      await buttonWithText(wrapper, 'Save').trigger('click')
      await flushPromises()
      expect(stores.assignments.updateAssignment).toHaveBeenLastCalledWith('a1', {
        priority_level: 'high',
        assignment_notes: 'Check literature'
      })
      expect(notify.showSuccess).toHaveBeenCalledWith('Assignment updated successfully')
    })

    it('reports a failed save', async () => {
      stores.assignments.updateAssignment.mockRejectedValue(new Error('locked'))
      const wrapper = mountManager()

      await wrapper.findAll('.row-stub')[0]!.findAll('button')[0]!.trigger('click')
      await buttonWithText(wrapper, 'Save').trigger('click')
      await flushPromises()

      expect(notify.showError).toHaveBeenCalledWith('Failed to update assignment')
    })

    it('reassigns the gene to a new curator', async () => {
      const wrapper = mountManager()

      await wrapper.findAll('.row-stub')[0]!.findAll('button')[1]!.trigger('click')
      byLabel(wrapper, 'New Curator').vm.$emit('update:model-value', reviewerUser.id)
      byLabel(wrapper, 'Transfer Note (Optional)').vm.$emit('update:model-value', 'Handover')
      await buttonWithText(wrapper, 'Reassign').trigger('click')
      await flushPromises()

      expect(api.assignCurator).toHaveBeenCalledWith('a1', 'reviewer-1')
      expect(notify.showSuccess).toHaveBeenCalledWith('Gene reassigned successfully')
      expect(stores.assignments.fetchAssignments).toHaveBeenCalled()
    })

    it('reports a failed reassignment', async () => {
      api.assignCurator.mockRejectedValue(new Error('forbidden'))
      const wrapper = mountManager()

      await wrapper.findAll('.row-stub')[0]!.findAll('button')[1]!.trigger('click')
      byLabel(wrapper, 'New Curator').vm.$emit('update:model-value', reviewerUser.id)
      await buttonWithText(wrapper, 'Reassign').trigger('click')
      await flushPromises()

      expect(notify.showError).toHaveBeenCalledWith('Failed to reassign gene')
    })

    it('does not reassign without a chosen curator', async () => {
      const wrapper = mountManager()

      await wrapper.findAll('.row-stub')[0]!.findAll('button')[1]!.trigger('click')
      await buttonWithText(wrapper, 'Reassign').trigger('click')
      await flushPromises()

      expect(api.assignCurator).not.toHaveBeenCalled()
    })
  })
})
