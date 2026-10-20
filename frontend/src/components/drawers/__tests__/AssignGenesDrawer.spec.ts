/**
 * AssignGenesDrawer Component Tests
 *
 * @see src/components/drawers/AssignGenesDrawer.vue
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import AssignGenesDrawer from '../AssignGenesDrawer.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const api = vi.hoisted(() => ({
  getGenes: vi.fn(),
  getAssignments: vi.fn(),
  createAssignment: vi.fn()
}))
vi.mock('@/api', () => ({
  genesAPI: { getGenes: api.getGenes },
  assignmentsAPI: { getAssignments: api.getAssignments, createAssignment: api.createAssignment }
}))

const scopes = vi.hoisted(() => ({ fetchMembers: vi.fn() }))
vi.mock('@/stores/scopes', () => ({ useScopesStore: () => scopes }))

const notifications = vi.hoisted(() => ({ addToast: vi.fn() }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => notifications }))

const passthrough = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  }
})

interface AssignVm {
  selectedGenes: string[]
  selectedCurator: string | null
  priority: string
  notes: string
  availableGenes: { gene_id: string }[]
  availableCurators: { user_id: string; role: string; email: string; full_name: string | null }[]
  handleAssign: () => Promise<void>
  getAvatarColor: (email: string) => string
  getInitials: (name: string) => string
  getRoleColor: (role: string) => string
}

const genes = {
  genes: [
    { id: 'g1', hgnc_id: 'HGNC:1100', approved_symbol: 'BRCA1' },
    { id: 'g2', hgnc_id: 'HGNC:11998', approved_symbol: 'TP53' }
  ]
}
const members = [
  { user_id: 'u1', user_email: 'ada@example.org', user_full_name: 'Ada Lovelace', role: 'curator' },
  { user_id: 'u2', user_email: 'grace@example.org', user_full_name: null, role: 'admin' },
  { user_id: 'u3', user_email: 'view@example.org', user_full_name: 'Viewer', role: 'viewer' }
]

let wrapper: VueWrapper | undefined

function mountDrawer(overrides: { modelValue?: boolean; scopeId?: string } = {}) {
  wrapper = mount(AssignGenesDrawer, {
    props: { modelValue: true, scopeId: 'scope-1', ...overrides },
    global: { stubs: { VNavigationDrawer: passthrough } }
  })
  return wrapper
}

function vmOf(w: VueWrapper) {
  return w.vm as unknown as AssignVm
}

describe('AssignGenesDrawer', () => {
  beforeEach(() => {
    api.getGenes.mockResolvedValue(genes)
    api.getAssignments.mockResolvedValue({ assignments: [{ gene_id: 'g2' }] })
    api.createAssignment.mockResolvedValue({})
    scopes.fetchMembers.mockResolvedValue(members)
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    vi.clearAllMocks()
  })

  it('loads unassigned genes and assignable curators when opened', async () => {
    const vm = vmOf(mountDrawer())
    await flushPromises()

    expect(api.getAssignments).toHaveBeenCalledWith({ scope_id: 'scope-1' })
    expect(vm.availableGenes.map(g => g.gene_id)).toEqual(['g1'])
    expect(vm.availableCurators.map(c => c.user_id)).toEqual(['u1', 'u2'])
    expect(vm.availableCurators[0]).toMatchObject({
      email: 'ada@example.org',
      full_name: 'Ada Lovelace'
    })
  })

  it('loads data on mount only when already open', async () => {
    mountDrawer({ modelValue: false, scopeId: 'scope-1' })
    await flushPromises()

    expect(api.getGenes).not.toHaveBeenCalled()
  })

  it('reloads on open and resets the form on close', async () => {
    const w = mountDrawer({ modelValue: false, scopeId: 'scope-1' })
    const vm = vmOf(w)
    vm.selectedGenes = ['g1']

    await w.setProps({ modelValue: true })
    await flushPromises()
    expect(api.getGenes).toHaveBeenCalledTimes(1)

    await w.setProps({ modelValue: false })
    expect(vm.selectedGenes).toEqual([])
    expect(vm.priority).toBe('normal')
  })

  it('creates one assignment per selected gene and reports success', async () => {
    const w = mountDrawer()
    await flushPromises()
    const vm = vmOf(w)
    vm.selectedGenes = ['g1', 'g2']
    vm.selectedCurator = 'u1'
    vm.priority = 'high'
    vm.notes = 'urgent'
    await w.vm.$nextTick()

    await vm.handleAssign()
    await flushPromises()

    expect(api.createAssignment).toHaveBeenCalledTimes(2)
    expect(api.createAssignment).toHaveBeenCalledWith({
      gene_id: 'g1',
      scope_id: 'scope-1',
      assigned_curator_id: 'u1',
      priority_level: 'high',
      assignment_notes: 'urgent'
    })
    expect(notifications.addToast).toHaveBeenCalledWith(
      '2 gene(s) assigned successfully',
      'success'
    )
    expect(w.emitted('assigned')).toHaveLength(1)
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('sends null for empty notes', async () => {
    const w = mountDrawer()
    await flushPromises()
    const vm = vmOf(w)
    vm.selectedGenes = ['g1']
    vm.selectedCurator = 'u1'
    await w.vm.$nextTick()

    await vm.handleAssign()

    expect(api.createAssignment).toHaveBeenCalledWith(
      expect.objectContaining({ assignment_notes: null })
    )
  })

  it('does not assign when validation fails', async () => {
    const w = mountDrawer()
    await flushPromises()
    const vm = vmOf(w)
    vm.selectedGenes = []

    await vm.handleAssign()

    expect(api.createAssignment).not.toHaveBeenCalled()
  })

  it('reports a failed assignment', async () => {
    api.createAssignment.mockRejectedValue(new Error('conflict'))
    const w = mountDrawer()
    await flushPromises()
    const vm = vmOf(w)
    vm.selectedGenes = ['g1']
    vm.selectedCurator = 'u1'
    await w.vm.$nextTick()

    await vm.handleAssign()

    expect(notifications.addToast).toHaveBeenCalledWith('Failed to assign genes', 'error')
    expect(w.emitted('assigned')).toBeUndefined()
  })

  it('reports gene and curator loading failures', async () => {
    api.getGenes.mockRejectedValue(new Error('down'))
    scopes.fetchMembers.mockRejectedValue(new Error('down'))
    mountDrawer()
    await flushPromises()

    expect(notifications.addToast).toHaveBeenCalledWith('Failed to load genes', 'error')
    expect(notifications.addToast).toHaveBeenCalledWith('Failed to load curators', 'error')
  })

  it('shows the selection count on the assign button', async () => {
    const w = mountDrawer()
    await flushPromises()
    vmOf(w).selectedGenes = ['g1', 'g2']
    await w.vm.$nextTick()

    expect(w.text()).toContain('Assign (2)')
  })

  it('derives avatar color, initials and role color', () => {
    const vm = vmOf(mountDrawer())

    expect(['primary', 'secondary', 'success', 'info', 'warning']).toContain(
      vm.getAvatarColor('ada@example.org')
    )
    expect(vm.getInitials('Ada Lovelace')).toBe('AL')
    expect(vm.getRoleColor('admin')).toBe('error')
    expect(vm.getRoleColor('viewer')).toBe('grey')
    expect(vm.getRoleColor('unknown')).toBe('grey')
  })

  it('emits update:modelValue false from Cancel', async () => {
    const w = mountDrawer()
    await flushPromises()
    const cancel = w.findAll('button').find(b => b.text().trim() === 'Cancel')

    await cancel?.trigger('click')

    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })
})
