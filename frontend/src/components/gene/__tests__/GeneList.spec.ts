import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GeneList from '../GeneList.vue'
import GeneCard from '../GeneCard.vue'
import GeneRowActions from '../GeneRowActions.vue'
import { assignmentsAPI, precurationsAPI, curationsAPI } from '@/api'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())
const push = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({ user: { role: 'admin' } as { role: string } | null }))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authState }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
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
  filterStatus: string | null
  filterCurator: string | null
  viewMode: string
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
  handleGeneRevalidated(result: { external_data?: unknown } | null): void
  openAssignModal(ids?: string[]): void
}

function internals(wrapper: { vm: unknown }): GeneListVm {
  return wrapper.vm as GeneListVm
}

const assignments = [
  {
    id: 'a-1',
    gene_id: 'g-1',
    gene: { gene_symbol: 'BRCA1', gene_name: 'BRCA1 gene', hgnc_id: 'HGNC:1100' },
    assigned_curator_id: 'u-1',
    curator: { full_name: 'Ada Lovelace' },
    priority: 'high',
    status: 'in_progress',
    due_date: '2025-06-01'
  },
  {
    assignment_id: 'a-2',
    gene_id: 'g-2',
    gene_symbol: 'TP53',
    gene_name: 'tumor protein',
    gene_hgnc_id: 'HGNC:11998',
    priority_level: 'low',
    status: 'completed'
  }
]

const stubs = {
  TableSkeleton: {
    props: ['items', 'headers', 'loading'],
    template:
      '<table><tbody><template v-for="item in items" :key="item.assignment_id || item.gene_id"><slot name="item" :item="item" /></template></tbody></table>'
  },
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
    authState.user = { role: 'admin' }
    getAssignments.mockResolvedValue(assignments as never)
    getPrecurations.mockResolvedValue({ precurations: [] } as never)
    getCurations.mockResolvedValue({ curations: [] } as never)
  })

  describe('loading', () => {
    it('loads the scope assignments and maps them for display', async () => {
      const wrapper = await mountList()

      expect(getAssignments).toHaveBeenCalledWith('scope-1')
      const genes = internals(wrapper).filteredGenes
      expect(genes.map(g => g.gene_id)).toEqual(['g-1', 'g-2'])
      expect(wrapper.text()).toContain('BRCA1')
      expect(wrapper.text()).toContain('Ada Lovelace')
      expect(wrapper.text()).toContain('Unassigned')
      expect(wrapper.text()).toContain('TP53')
      expect(logger.debug).toHaveBeenCalledWith('Genes loaded', { count: 2, scope_id: 'scope-1' })
    })

    it('reports a failed load with a toast', async () => {
      getAssignments.mockRejectedValue({ message: 'offline' })

      await mountList()

      expect(logger.error).toHaveBeenCalledWith('Failed to fetch genes', { error: 'offline' })
      expect(addToast).toHaveBeenCalledWith('Failed to load genes', 'error')
    })

    it('shows precuration and curation status chips from the workflow maps', async () => {
      getPrecurations.mockResolvedValue({
        precurations: [{ id: 'p-1', gene_id: 'g-1', status: 'approved', updated_at: '2025-01-01' }]
      } as never)
      getCurations.mockResolvedValue({
        curations: [{ id: 'c-2', gene_id: 'g-2', status: 'active', updated_at: '2025-01-01' }]
      } as never)

      const wrapper = await mountList()

      expect(wrapper.text()).toContain('Ready for Curation')
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
    it('shows the add and assign buttons to admins', async () => {
      const wrapper = await mountList()

      expect(wrapper.text()).toContain('Add Genes')
      expect(wrapper.text()).toContain('Assign to Curator')
    })

    it('hides the add and assign buttons for viewers', async () => {
      authState.user = { role: 'viewer' }
      const wrapper = await mountList()

      expect(wrapper.text()).not.toContain('Add Genes')
      expect(wrapper.text()).not.toContain('Assign to Curator')
    })

    it('passes removal permission only to reviewers and scope admins', async () => {
      authState.user = { role: 'reviewer' }
      const wrapper = await mountList()

      const row = wrapper.findComponent(GeneRowActions)
      expect(row.props('canRemoveGenes')).toBe(true)
      expect(row.props('canAssignGenes')).toBe(false)
    })

    it('treats a user without a role as having no permissions', async () => {
      authState.user = null
      const wrapper = await mountList()

      expect(wrapper.findComponent(GeneRowActions).props('canAssignGenes')).toBe(false)
      expect(wrapper.findComponent(GeneRowActions).props('canRemoveGenes')).toBe(false)
    })
  })

  describe('filtering', () => {
    it('filters by search text across symbol and name', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.search = 'tumor'
      await flushPromises()
      expect(vm.filteredGenes.map(g => g.gene_id)).toEqual(['g-2'])

      vm.search = 'brca'
      await flushPromises()
      expect(vm.filteredGenes.map(g => g.gene_id)).toEqual(['g-1'])
    })

    it('filters by status and by curator', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.filterStatus = 'completed'
      await flushPromises()
      expect(vm.filteredGenes.map(g => g.gene_id)).toEqual(['g-2'])

      vm.filterStatus = null
      vm.filterCurator = 'u-1'
      await flushPromises()
      expect(vm.filteredGenes.map(g => g.gene_id)).toEqual(['g-1'])
    })

    it('shows the empty state with a clear-filters action when nothing matches', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)

      vm.search = 'nothing-matches'
      await flushPromises()

      expect(wrapper.text()).toContain('No genes match your filters')
      expect(wrapper.text()).toContain('Try adjusting your search or filter criteria.')

      vm.clearFilters()
      await flushPromises()
      expect(vm.search).toBe('')
      expect(vm.filteredGenes).toHaveLength(2)
    })

    it('shows the assign prompt when the scope has no genes', async () => {
      getAssignments.mockResolvedValue([] as never)
      const wrapper = await mountList()

      expect(wrapper.text()).toContain('No genes assigned')
      expect(wrapper.text()).toContain('Assign Genes')
    })
  })

  describe('views', () => {
    it('renders cards in card view with the workflow shared to each card', async () => {
      const wrapper = await mountList()

      internals(wrapper).viewMode = 'cards'
      await flushPromises()

      const cards = wrapper.findAllComponents(GeneCard)
      expect(cards).toHaveLength(2)
      expect(cards[0]!.props('gene')).toMatchObject({ gene_id: 'g-1' })
      expect(cards[0]!.props('workflow')).toBeDefined()
    })

    it('shows skeleton cards while loading in card view', async () => {
      getAssignments.mockReturnValue(new Promise(() => {}) as never)
      const wrapper = mount(GeneList, { props: { scopeId: 'scope-1' }, global: { stubs } })
      internals(wrapper).viewMode = 'cards'
      await flushPromises()

      expect(wrapper.findAll('.v-skeleton-loader').length).toBeGreaterThan(0)
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
        'Genes added to catalog. You can now assign them to curators.',
        'success'
      )
      vm.handleGenesAssigned()
      expect(addToast).toHaveBeenCalledWith('Genes assigned successfully', 'success')
      vm.handleGeneReassigned()
      vm.handleGeneEdited()

      expect(getAssignments).toHaveBeenCalledTimes(4)
    })

    it('refreshes only when a revalidation returns external data', async () => {
      const wrapper = await mountList()
      const vm = internals(wrapper)
      getAssignments.mockClear()

      vm.handleGeneRevalidated({ external_data: undefined })
      vm.handleGeneRevalidated(null)
      expect(getAssignments).not.toHaveBeenCalled()

      vm.handleGeneRevalidated({ external_data: { symbol: 'BRCA1' } })
      expect(getAssignments).toHaveBeenCalledTimes(1)
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
})
