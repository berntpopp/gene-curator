import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GeneList from '../GeneList.vue'
import GeneRowActions from '../GeneRowActions.vue'
import { assignmentsAPI, precurationsAPI, curationsAPI } from '@/api'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())
const push = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({ isAdmin: false }))
const scopeState = vi.hoisted(() => ({
  currentUserRole: 'admin' as string | null,
  currentScope: null as { default_workflow_pair_id: string | null } | null
}))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authState }))
vi.mock('@/stores/scopes', () => ({ useScopesStore: () => scopeState }))
const routeState = vi.hoisted(() => ({ query: {} as Record<string, string> }))
const replace = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => routeState
}))
vi.mock('@/api', () => ({
  assignmentsAPI: { getAssignmentsByScope: vi.fn(), removeAssignment: vi.fn() },
  precurationsAPI: { getPrecurations: vi.fn(), completePrecuration: vi.fn() },
  curationsAPI: { getCurations: vi.fn() }
}))

const getAssignments = vi.mocked(assignmentsAPI.getAssignmentsByScope)
const removeAssignment = vi.mocked(assignmentsAPI.removeAssignment)
const getPrecurations = vi.mocked(precurationsAPI.getPrecurations)
const completePrecuration = vi.mocked(precurationsAPI.completePrecuration)
const getCurations = vi.mocked(curationsAPI.getCurations)

/** Component state read through wrapper.vm in these tests. */
interface GeneListVm {
  search: string
  showAssignModal: boolean
  preSelectedGeneIds: string[]
  showReassignModal: boolean
  selectedGeneForReassign: { gene_id: string } | null
  showEditModal: boolean
  showRemoveConfirm: boolean
  selectedGeneForRemoval: { gene_id: string; gene_symbol: string; assignment_id: string } | null
  showGeneDetailModal: boolean
  selectedGeneForDetail: { gene_id: string } | null
  filteredGenes: Array<{ gene_id: string }>
  clearFilters(): void
  stageCounts: Record<string, number>
  detailContext: { curator: string; stage: string; curationLink: string } | undefined
  viewGene(gene: unknown): void
  startPrecuration(gene: unknown): void
  startCuration(gene: unknown): void
  viewCuration(gene: unknown): void
  completePrecuration(gene: unknown): Promise<void>
  reassignGene(gene: unknown): void
  editGeneAssignment(gene: unknown): void
  confirmRemoveGene(gene: unknown): void
  cancelRemoveGene(): void
  removeGeneFromScope(): Promise<void>
  handleGenesAdded(): void
  handleGenesAssigned(): void
  handleGeneReassigned(): void
  handleGeneEdited(): void
  openAssignModal(ids?: string[]): void
}

function internals(wrapper: { vm: unknown }): GeneListVm {
  return wrapper.vm as GeneListVm
}

const assignments = [
  {
    id: 'a-1',
    gene_id: 'g-1',
    gene_symbol: 'BRCA1',
    gene_hgnc_id: 'HGNC:1100',
    assigned_curator_id: 'u-1',
    curator_name: 'Ada Lovelace',
    priority: 'high',
    has_active_work: true
  },
  {
    id: 'a-2',
    gene_id: 'g-2',
    gene_symbol: 'TP53',
    gene_hgnc_id: 'HGNC:11998',
    assigned_curator_id: null,
    curator_name: null,
    priority: 'low',
    has_active_work: false
  }
]

const stubs = {
  DataTable: {
    props: ['items', 'headers', 'filterDefs', 'itemsLength'],
    template:
      '<div><slot name="toolbar-actions" /><div v-for="item in items" :key="item.assignment_id" class="row"><slot name="item.select" :item="item" /><slot name="item.gene_symbol" :item="item" /><slot name="item.curator_name" :item="item" /><slot name="item.stage" :item="item" /><slot name="item.priority" :item="item" /><slot name="item.updated_at" :item="item" /><slot name="item.actions" :item="item" /></div><slot v-if="!items.length" name="no-data" /></div>'
  },
  GeneBulkBar: true,
  PasteGenesDialog: true,
  VDialog: { template: '<div><slot /></div>' },
  AddGeneModal: true,
  AssignCuratorModal: true,
  GeneDetailModal: true,
  ReassignGeneModal: true,
  EditGeneAssignmentModal: true
}

async function mountList(scopeId = 'scope-1') {
  const wrapper = mount(GeneList, { props: { scopeId }, global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('GeneList', () => {
  beforeEach(() => {
    // Reset only this file's mocks: resetAllMocks would also wipe the global matchMedia stub.
    ;[getAssignments, removeAssignment, getPrecurations, completePrecuration, getCurations].forEach(
      m => m.mockReset()
    )
    ;[addToast, push, logger.debug, logger.info, logger.warn, logger.error].forEach(m =>
      m.mockReset()
    )
    routeState.query = {}
    authState.isAdmin = false
    scopeState.currentUserRole = 'admin'
    scopeState.currentScope = { default_workflow_pair_id: 'wp-1' }
    getAssignments.mockResolvedValue(assignments as never)
    getPrecurations.mockResolvedValue({ precurations: [] } as never)
    getCurations.mockResolvedValue({ curations: [] } as never)
  })

  describe('loading', () => {
    it('loads the scope assignments and maps them for display', async () => {
      const wrapper = await mountList()

      expect(getAssignments).toHaveBeenCalledWith('scope-1', { limit: 1000 })
      const genes = internals(wrapper).filteredGenes
      expect(genes.map(g => g.gene_id)).toEqual(['g-1', 'g-2'])
      expect(wrapper.text()).toContain('BRCA1')
      expect(wrapper.text()).toContain('Ada Lovelace')
      expect(wrapper.text()).toContain('Unassigned')
      expect(wrapper.text()).toContain('HGNC:1100')
      expect(wrapper.text()).toContain('TP53')
      expect(logger.debug).toHaveBeenCalledWith('Genes loaded', { count: 2, scope_id: 'scope-1' })
    })

    it('reports a failed load with a toast', async () => {
      getAssignments.mockRejectedValue({ message: 'offline' })

      await mountList()

      expect(logger.error).toHaveBeenCalledWith('Failed to fetch genes', { error: 'offline' })
      expect(addToast).toHaveBeenCalledWith('Failed to load genes', 'error')
    })

    it('derives the stage of each row from the workflow maps', async () => {
      getPrecurations.mockResolvedValue({
        precurations: [{ id: 'p-1', gene_id: 'g-1', status: 'approved', updated_at: '2025-01-01' }]
      } as never)
      getCurations.mockResolvedValue({
        curations: [{ id: 'c-2', gene_id: 'g-2', status: 'active', updated_at: '2025-01-01' }]
      } as never)

      const wrapper = await mountList()

      expect(wrapper.text()).toContain('Curation')
      expect(wrapper.text()).toContain('Active')
    })

    it('still renders genes when the status lookups fail', async () => {
      getPrecurations.mockRejectedValue(new Error('x'))
      getCurations.mockRejectedValue(new Error('y'))

      const wrapper = await mountList()

      expect(internals(wrapper).filteredGenes).toHaveLength(2)
      expect(logger.error).toHaveBeenCalledWith('Failed to fetch precuration statuses', {
        error: 'x'
      })
      expect(logger.error).toHaveBeenCalledWith('Failed to fetch curation statuses', { error: 'y' })
    })
  })

  describe('permissions', () => {
    it('shows the add and assign buttons to scope admins and application admins', async () => {
      scopeState.currentUserRole = 'admin'
      let wrapper = await mountList()
      expect(wrapper.text()).toContain('Add genes')

      authState.isAdmin = true
      scopeState.currentUserRole = 'viewer'
      wrapper = await mountList()
      expect(wrapper.text()).toContain('Add genes')
    })

    it('hides the add and assign buttons for curators, reviewers and viewers', async () => {
      for (const role of ['curator', 'viewer', 'reviewer']) {
        scopeState.currentUserRole = role
        const wrapper = await mountList()

        expect(wrapper.text()).not.toContain('Add genes')
      }
    })

    it('lets only the application admin remove genes, whatever the scope role', async () => {
      scopeState.currentUserRole = 'admin'
      let row = (await mountList()).findComponent(GeneRowActions)
      expect(row.props('canRemoveGenes')).toBe(false)
      expect(row.props('canAssignGenes')).toBe(true)
      expect(row.props('canReassign')).toBe(true)

      scopeState.currentUserRole = 'curator'
      row = (await mountList()).findComponent(GeneRowActions)
      expect(row.props('canAssignGenes')).toBe(true)
      expect(row.props('canReassign')).toBe(false)

      authState.isAdmin = true
      scopeState.currentUserRole = 'viewer'
      row = (await mountList()).findComponent(GeneRowActions)
      expect(row.props('canRemoveGenes')).toBe(true)
      expect(row.props('canAssignGenes')).toBe(false)
    })

    it('grants nothing without a scope role', async () => {
      scopeState.currentUserRole = null
      const wrapper = await mountList()

      expect(wrapper.findComponent(GeneRowActions).props('canAssignGenes')).toBe(false)
      expect(wrapper.findComponent(GeneRowActions).props('canRemoveGenes')).toBe(false)
    })
  })

  describe('filtering', () => {
    it('filters by search text across symbol and HGNC id', async () => {
      routeState.query = { q: 'hgnc:119' }
      const wrapper = await mountList()
      expect(internals(wrapper).filteredGenes.map(g => g.gene_id)).toEqual(['g-2'])
    })

    it('filters by stage, curator and priority from the URL', async () => {
      routeState.query = { stage: 'unassigned' }
      expect(internals(await mountList()).filteredGenes.map(g => g.gene_id)).toEqual(['g-2'])
      routeState.query = { curator: 'u-1' }
      expect(internals(await mountList()).filteredGenes.map(g => g.gene_id)).toEqual(['g-1'])
      routeState.query = { priority: 'low' }
      expect(internals(await mountList()).filteredGenes.map(g => g.gene_id)).toEqual(['g-2'])
    })

    it('counts genes per stage', async () => {
      const vm = internals(await mountList())
      expect(vm.stageCounts).toMatchObject({ unassigned: 1, precuration: 1, curation: 0 })
    })

    it('sorts by stage and priority', async () => {
      routeState.query = { sort: 'priority', order: 'desc' }
      expect(internals(await mountList()).filteredGenes.map(g => g.gene_id)).toEqual(['g-2', 'g-1'])
      routeState.query = { sort: 'stage' }
      expect(internals(await mountList()).filteredGenes.map(g => g.gene_id)).toEqual(['g-2', 'g-1'])
    })

    it('shows one empty state with a clear-filters action when nothing matches', async () => {
      routeState.query = { q: 'nothing-matches' }
      const wrapper = await mountList()
      expect(wrapper.findAll('[data-testid=table-empty]')).toHaveLength(1)
      expect(wrapper.text()).toContain('No genes match the filters')
      await wrapper.find('[data-testid=table-empty] button').trigger('click')
      await flushPromises()
      expect(replace).toHaveBeenCalled()
    })

    it('invites admins to add genes when the scope is empty', async () => {
      getAssignments.mockResolvedValue([] as never)
      const wrapper = await mountList()
      expect(wrapper.text()).toContain('No genes in this scope yet')
      expect(wrapper.text()).toContain('Add genes')
    })

    it('sets and clears the stage filter from the strip', async () => {
      const wrapper = await mountList()
      wrapper.findComponent({ name: 'ScopeStageStrip' }).vm.$emit('update:modelValue', 'curation')
      await flushPromises()
      expect(replace).toHaveBeenCalled()
      wrapper.findComponent({ name: 'ScopeStageStrip' }).vm.$emit('update:modelValue', undefined)
      await flushPromises()
      expect(replace).toHaveBeenCalledTimes(2)
    })
  })

  describe('large scopes and bulk results', () => {
    it('loads and counts more than the default page of 100 assignments', async () => {
      const many = Array.from({ length: 250 }, (_, i) => ({
        ...assignments[1]!,
        id: `a-${i}`,
        gene_id: `g-${i}`
      }))
      getAssignments.mockResolvedValue(many as never)
      const vm = internals(await mountList())
      expect(getAssignments).toHaveBeenCalledWith('scope-1', { limit: 1000 })
      expect(vm.filteredGenes).toHaveLength(250)
      expect(vm.stageCounts.unassigned).toBe(250)
    })

    it('keeps only the failed genes selected after a bulk run', async () => {
      const wrapper = await mountList()
      ;(internals(wrapper) as unknown as { selectedIds: string[] }).selectedIds = ['g-1', 'g-2']
      wrapper.findComponent({ name: 'GeneBulkBar' }).vm.$emit('changed', ['g-2'])
      await flushPromises()
      expect((internals(wrapper) as unknown as { selectedIds: string[] }).selectedIds).toEqual([
        'g-2'
      ])
    })

    it('offers only genes without a curator to the assign dialog', async () => {
      const wrapper = await mountList()
      ;(internals(wrapper) as unknown as { selectedIds: string[] }).selectedIds = ['g-1', 'g-2']
      wrapper.findComponent({ name: 'GeneBulkBar' }).vm.$emit('assign')
      expect(internals(wrapper).preSelectedGeneIds).toEqual(['g-2'])
    })
  })

  describe('gene detail context', () => {
    it('gives the detail dialog curator, stage and curation link of the row', async () => {
      getCurations.mockResolvedValue({
        curations: [{ id: 'c-1', gene_id: 'g-1', status: 'draft', updated_at: '2026-01-01' }]
      } as never)
      const wrapper = await mountList()
      const vm = internals(wrapper)
      expect(vm.detailContext).toBeUndefined()

      vm.viewGene({ gene_id: 'g-1' })
      await flushPromises()
      expect(vm.detailContext).toEqual({
        curator: 'Ada Lovelace',
        stage: 'Curation',
        curationLink: '/scopes/scope-1/curations/c-1'
      })

      vm.viewGene({ gene_id: 'g-2' })
      await flushPromises()
      expect(vm.detailContext?.curationLink).toBe('')
    })

    it('sorts by another column', async () => {
      routeState.query = { sort: 'gene_symbol', order: 'desc' }
      const wrapper = await mountList()
      expect(internals(wrapper).filteredGenes.map(g => g.gene_id)).toEqual(['g-2', 'g-1'])
    })
  })

  describe('actions', () => {
    it('opens the add-gene and assign modals', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.openAssignModal(['g-1'])
      expect(vm.showAssignModal).toBe(true)
      expect(vm.preSelectedGeneIds).toEqual(['g-1'])

      vm.openAssignModal()
      expect(vm.preSelectedGeneIds).toEqual([])
    })

    it('opens gene details', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.viewGene(assignments[0] && { gene_id: 'g-1' })

      expect(vm.showGeneDetailModal).toBe(true)
      expect(vm.selectedGeneForDetail).toEqual({ gene_id: 'g-1' })
    })

    it('navigates to the precuration form and only to curation when approved', async () => {
      getPrecurations.mockResolvedValue({
        precurations: [{ id: 'p-1', gene_id: 'g-1', status: 'draft', updated_at: '2025-01-01' }]
      } as never)
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.startPrecuration({ gene_id: 'g-2' })
      expect(push).toHaveBeenCalledWith('/scopes/scope-1/genes/g-2/precuration/new')

      vm.startCuration({ gene_id: 'g-1' })
      expect(addToast).toHaveBeenCalledWith(
        'Complete and approve precuration before starting curation',
        'warning'
      )
      expect(push).toHaveBeenCalledTimes(1)
    })

    it('starts curation for an approved precuration', async () => {
      getPrecurations.mockResolvedValue({
        precurations: [{ id: 'p-1', gene_id: 'g-1', status: 'approved', updated_at: '2025-01-01' }]
      } as never)
      const wrapper = await mountList()

      internals(wrapper).startCuration({ gene_id: 'g-1' })

      expect(push).toHaveBeenCalledWith('/scopes/scope-1/genes/g-1/curation/new')
    })

    it('opens an existing curation, and does nothing without one', async () => {
      getCurations.mockResolvedValue({
        curations: [{ id: 'c-9', gene_id: 'g-1', status: 'draft', updated_at: '2025-01-01' }]
      } as never)
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.viewCuration({ gene_id: 'g-1' })
      expect(push).toHaveBeenCalledWith('/scopes/scope-1/curations/c-9')

      push.mockClear()
      vm.viewCuration({ gene_id: 'g-2' })
      expect(push).not.toHaveBeenCalled()
    })

    it('starts precuration instead of completing when none exists', async () => {
      const wrapper = await mountList()

      await internals(wrapper).completePrecuration({ gene_id: 'g-2' })

      expect(push).toHaveBeenCalledWith('/scopes/scope-1/genes/g-2/precuration/new')
      expect(completePrecuration).not.toHaveBeenCalled()
    })

    it('completes an existing precuration and refreshes the statuses', async () => {
      getPrecurations.mockResolvedValue({
        precurations: [{ id: 'p-1', gene_id: 'g-1', status: 'draft', updated_at: '2025-01-01' }]
      } as never)
      completePrecuration.mockResolvedValue({} as never)
      const wrapper = await mountList()
      getPrecurations.mockClear()

      await internals(wrapper).completePrecuration({ gene_id: 'g-1' })

      expect(completePrecuration).toHaveBeenCalledWith('p-1')
      expect(addToast).toHaveBeenCalledWith('Precuration completed successfully', 'success')
      expect(getPrecurations).toHaveBeenCalledTimes(1)
    })

    it('reports a failed precuration completion', async () => {
      getPrecurations.mockResolvedValue({
        precurations: [{ id: 'p-1', gene_id: 'g-1', status: 'draft', updated_at: '2025-01-01' }]
      } as never)
      completePrecuration.mockRejectedValue(new Error('locked'))
      const wrapper = await mountList()

      await internals(wrapper).completePrecuration({ gene_id: 'g-1' })

      expect(logger.error).toHaveBeenCalledWith('Failed to complete precuration', {
        error: 'locked'
      })
      expect(addToast).toHaveBeenCalledWith('Failed to complete precuration: locked', 'error')
    })

    it('opens the reassign and edit modals for a gene', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.reassignGene({ gene_id: 'g-1' })
      expect(vm.showReassignModal).toBe(true)
      expect(vm.selectedGeneForReassign).toEqual({ gene_id: 'g-1' })

      vm.editGeneAssignment({ gene_id: 'g-2' })
      expect(vm.showEditModal).toBe(true)
    })

    it('confirms and then removes a gene from the scope', async () => {
      removeAssignment.mockResolvedValue({} as never)
      const wrapper = await mountList()
      const vm = internals(wrapper)
      getAssignments.mockClear()

      vm.confirmRemoveGene({ gene_id: 'g-2', gene_symbol: 'TP53', assignment_id: 'a-2' })
      expect(vm.showRemoveConfirm).toBe(true)

      await vm.removeGeneFromScope()

      expect(removeAssignment).toHaveBeenCalledWith('a-2', 'Removed from scope via gene management')
      expect(addToast).toHaveBeenCalledWith('TP53 removed from scope', 'success')
      expect(vm.showRemoveConfirm).toBe(false)
      expect(vm.selectedGeneForRemoval).toBeNull()
      expect(getAssignments).toHaveBeenCalledTimes(1)
    })

    it('does nothing when the removal target has no assignment', async () => {
      const wrapper = await mountList()

      await internals(wrapper).removeGeneFromScope()

      expect(removeAssignment).not.toHaveBeenCalled()
    })

    it('reports a failed removal and keeps the dialog open', async () => {
      removeAssignment.mockRejectedValue({
        message: 'nope',
        response: { data: { detail: 'Forbidden' } }
      })
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.confirmRemoveGene({ gene_id: 'g-2', gene_symbol: 'TP53', assignment_id: 'a-2' })
      await vm.removeGeneFromScope()

      expect(addToast).toHaveBeenCalledWith('Failed to remove: Forbidden', 'error')
      expect(vm.showRemoveConfirm).toBe(true)
    })

    it('cancels the removal confirmation', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.confirmRemoveGene({ gene_id: 'g-2', gene_symbol: 'TP53', assignment_id: 'a-2' })
      vm.cancelRemoveGene()

      expect(vm.showRemoveConfirm).toBe(false)
      expect(vm.selectedGeneForRemoval).toBeNull()
    })

    it('refreshes after add, assign, reassign and edit events from the modals', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)
      getAssignments.mockClear()

      vm.handleGenesAdded()
      expect(addToast).toHaveBeenCalledWith(
        'Genes added to this scope. You can now assign them to curators.',
        'success'
      )
      vm.handleGenesAssigned()
      expect(addToast).toHaveBeenCalledWith('Genes assigned successfully', 'success')
      vm.handleGeneReassigned()
      vm.handleGeneEdited()

      expect(getAssignments).toHaveBeenCalledTimes(4)
    })

    it('wires the row action menu to the list handlers', async () => {
      const wrapper = await mountList()
      const row = wrapper.findAllComponents(GeneRowActions)[0]!

      row.vm.$emit('start-precuration', { gene_id: 'g-2' })
      expect(push).toHaveBeenCalledWith('/scopes/scope-1/genes/g-2/precuration/new')

      row.vm.$emit('reassign', { gene_id: 'g-1' })
      expect(internals(wrapper).showReassignModal).toBe(true)
    })
  })
  describe('selection and change events', () => {
    it('emits changed and clears the selection after a change', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper) as unknown as { selectedIds: string[] }
      vm.selectedIds = ['g-1', 'g-2']

      internals(wrapper).handleGenesAssigned()

      expect(wrapper.emitted('changed')).toHaveLength(1)
      expect(vm.selectedIds).toEqual([])
    })

    it('hides the bulk bar from users who cannot assign', async () => {
      scopeState.currentUserRole = 'viewer'
      expect((await mountList()).findComponent({ name: 'GeneBulkBar' }).exists()).toBe(false)
    })

    it('opens the assign dialog from the bulk bar with the selection', async () => {
      const wrapper = await mountList()
      ;(internals(wrapper) as unknown as { selectedIds: string[] }).selectedIds = ['g-2']
      wrapper.findComponent({ name: 'GeneBulkBar' }).vm.$emit('assign')
      expect(internals(wrapper).preSelectedGeneIds).toEqual(['g-2'])
      expect(internals(wrapper).showAssignModal).toBe(true)
    })
  })

  describe('scope without a methodology', () => {
    it('shows one banner and blocks starting a precuration', async () => {
      scopeState.currentScope = { default_workflow_pair_id: null }
      const wrapper = await mountList()

      expect(wrapper.text()).toContain('This scope has no methodology yet')
      expect(wrapper.text()).toContain('Choose one in Settings')
      expect(wrapper.findComponent(GeneRowActions).props('startBlockedReason')).toBe(
        'This scope has no methodology yet'
      )

      internals(wrapper).startPrecuration(assignments[0])
      expect(push).not.toHaveBeenCalled()
    })

    it('tells non-admins to ask a scope admin', async () => {
      scopeState.currentScope = { default_workflow_pair_id: null }
      scopeState.currentUserRole = 'curator'
      const wrapper = await mountList()

      expect(wrapper.text()).toContain('Ask a scope admin')
    })

    it('shows no banner when the scope has a workflow pair', async () => {
      const wrapper = await mountList()
      expect(wrapper.text()).not.toContain('no methodology')
    })
  })
})
