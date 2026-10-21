import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AssignCuratorModal from '../AssignCuratorModal.vue'
import { assignmentsAPI } from '@/api'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())
const fetchMembers = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/stores/scopes', () => ({ useScopesStore: () => ({ fetchMembers }) }))
vi.mock('@/composables/useRoleColors', () => ({
  useRoleColors: () => ({ getRoleColor: () => 'grey' })
}))
vi.mock('@/api', () => ({
  assignmentsAPI: { getAssignmentsByScope: vi.fn(), bulkAssignGenes: vi.fn() }
}))

const getAssignmentsByScope = vi.mocked(assignmentsAPI.getAssignmentsByScope)
const bulkAssignGenes = vi.mocked(assignmentsAPI.bulkAssignGenes)

const scopeAssignments = [
  { gene_id: 'g-1', gene_symbol: 'BRCA1', gene_hgnc_id: 'HGNC:1100', is_active: true },
  {
    gene_id: 'g-2',
    gene_symbol: 'TP53',
    gene_hgnc_id: 'HGNC:11998',
    is_active: true,
    assigned_curator_id: 'u-1'
  },
  {
    gene_id: 'g-3',
    gene_symbol: 'MLH1',
    gene_hgnc_id: 'HGNC:7127',
    is_active: true,
    assigned_curator_id: null
  }
]

const members = [
  { user_id: 'u-1', role: 'curator', user_full_name: 'Ada Lovelace', user_email: 'ada@x.org' },
  { user_id: 'u-9', role: 'reviewer', user_full_name: 'Rev', user_email: 'r@x.org' }
]

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

/** Internal state read through wrapper.vm. */
interface AssignVm {
  availableGenes: Array<{ id: string }>
  availableCurators: Array<{ user_id: string; displayName: string }>
  selectedGenes: Array<{ id: string }>
  selectedCurator: { user_id: string } | null
  allGenesSelected: boolean
  someGenesSelected: boolean
  canSubmit: unknown
  optionalSettingsCount: number
  hasOptionalSettings: unknown
  priority: string
  notes: string
  toggleSelectAll(): void
  isGeneSelected(gene: { id: string }): boolean
  handleSubmit(): Promise<void>
  handleCancel(): void
}

function internals(wrapper: { vm: unknown }): AssignVm {
  return wrapper.vm as AssignVm
}

async function mountModal(props: Record<string, unknown> = {}) {
  const wrapper = mount(AssignCuratorModal, {
    props: { modelValue: true, scopeId: 'scope-1', ...props },
    global: { stubs: { VDialog: dialogStub } }
  })
  await flushPromises()
  return wrapper
}

describe('AssignCuratorModal', () => {
  beforeEach(() => {
    getAssignmentsByScope.mockReset()
    bulkAssignGenes.mockReset()
    fetchMembers.mockReset()
    addToast.mockReset()
    logger.error.mockReset()
    getAssignmentsByScope.mockResolvedValue(scopeAssignments as never)
    fetchMembers.mockResolvedValue(members)
  })

  it('offers only scope genes that have no curator yet', async () => {
    const wrapper = await mountModal()

    expect(getAssignmentsByScope).toHaveBeenCalledWith('scope-1', { limit: 1000 })
    expect(internals(wrapper).availableGenes).toEqual([
      { id: 'g-1', approved_symbol: 'BRCA1', hgnc_id: 'HGNC:1100' },
      { id: 'g-3', approved_symbol: 'MLH1', hgnc_id: 'HGNC:7127' }
    ])
  })

  it('loads only curator-capable members', async () => {
    const wrapper = await mountModal()

    expect(fetchMembers).toHaveBeenCalledWith('scope-1')
    expect(internals(wrapper).availableCurators.map(c => c.user_id)).toEqual(['u-1'])
    expect(internals(wrapper).availableCurators[0]?.displayName).toBe('Ada Lovelace')
  })

  it('reports a failed gene load', async () => {
    getAssignmentsByScope.mockRejectedValue({ message: 'down' })
    await mountModal()

    expect(logger.error).toHaveBeenCalledWith('Failed to fetch available genes', { error: 'down' })
    expect(addToast).toHaveBeenCalledWith('Failed to load genes', 'error')
  })

  it('reports a failed curator load', async () => {
    fetchMembers.mockRejectedValue({ message: 'forbidden' })
    await mountModal()

    expect(logger.error).toHaveBeenCalledWith('Failed to fetch curators', { error: 'forbidden' })
    expect(addToast).toHaveBeenCalledWith('Failed to load curators', 'error')
  })

  it('selects and clears all available genes', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.toggleSelectAll()
    expect(vm.allGenesSelected).toBe(true)
    expect(vm.isGeneSelected({ id: 'g-1' })).toBe(true)
    expect(vm.someGenesSelected).toBe(false)

    vm.toggleSelectAll()
    expect(vm.selectedGenes).toEqual([])
    expect(vm.someGenesSelected).toBe(false)
  })

  it('reports partial selection', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.selectedGenes = [{ id: 'g-1' }]
    expect(vm.someGenesSelected).toBe(true)
    expect(vm.allGenesSelected).toBe(false)
  })

  it('counts optional settings that differ from defaults', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    expect(vm.hasOptionalSettings).toBeFalsy()
    vm.priority = 'high'
    vm.notes = 'urgent'
    expect(vm.optionalSettingsCount).toBe(2)
    expect(vm.hasOptionalSettings).toBeTruthy()
  })

  it('assigns all selected genes in one request', async () => {
    bulkAssignGenes.mockResolvedValue({ total_created: 2 } as never)
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.selectedGenes = [{ id: 'g-1' }, { id: 'g-3' }]
    vm.selectedCurator = { user_id: 'u-1', full_name: 'Ada Lovelace' } as never
    vm.priority = 'high'
    vm.notes = 'please'
    await flushPromises()
    await vm.handleSubmit()

    expect(bulkAssignGenes).toHaveBeenCalledTimes(1)
    expect(bulkAssignGenes).toHaveBeenCalledWith({
      gene_ids: ['g-1', 'g-3'],
      scope_id: 'scope-1',
      assigned_curator_id: 'u-1',
      priority_level: 'high',
      assignment_notes: 'please'
    })
    expect(addToast).toHaveBeenCalledWith('2 gene(s) assigned to Ada Lovelace', 'success')
    expect(wrapper.emitted('assigned')).toHaveLength(1)
  })

  it('warns when some genes were skipped', async () => {
    bulkAssignGenes.mockResolvedValue({ total_created: 1 } as never)
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.selectedGenes = [{ id: 'g-1' }, { id: 'g-3' }]
    vm.selectedCurator = { user_id: 'u-1', full_name: 'Ada' } as never
    await flushPromises()
    await vm.handleSubmit()

    expect(addToast).toHaveBeenCalledWith('1 gene(s) assigned to Ada (1 skipped)', 'warning')
  })

  it('does nothing without a curator or genes', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    expect(vm.canSubmit).toBeFalsy()
    await vm.handleSubmit()

    expect(bulkAssignGenes).not.toHaveBeenCalled()
  })

  it('reports a failed assignment with the server detail', async () => {
    bulkAssignGenes.mockRejectedValue({ message: 'x', response: { data: { detail: 'Quota' } } })
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.selectedGenes = [{ id: 'g-1' }]
    vm.selectedCurator = { user_id: 'u-1' }
    await flushPromises()
    await vm.handleSubmit()

    expect(addToast).toHaveBeenCalledWith('Failed to assign genes: Quota', 'error')
    expect(wrapper.emitted('assigned')).toBeUndefined()
  })

  it('resets the form when cancelled', async () => {
    const wrapper = await mountModal()
    const vm = internals(wrapper)

    vm.selectedGenes = [{ id: 'g-1' }]
    vm.notes = 'x'
    vm.handleCancel()

    expect(vm.selectedGenes).toEqual([])
    expect(vm.notes).toBe('')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })
})
