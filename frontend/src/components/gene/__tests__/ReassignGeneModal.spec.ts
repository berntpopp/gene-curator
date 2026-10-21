import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ReassignGeneModal from '../ReassignGeneModal.vue'
import { assignmentsAPI } from '@/api'
import type { GeneRow } from '../types'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())
const fetchMembers = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/stores/scopes', () => ({ useScopesStore: () => ({ fetchMembers }) }))
vi.mock('@/composables/useRoleColors', () => ({
  useRoleColors: () => ({ getRoleColor: (role: string) => (role === 'curator' ? 'blue' : 'grey') })
}))
vi.mock('@/api', () => ({ assignmentsAPI: { assignCurator: vi.fn() } }))

const assignCurator = vi.mocked(assignmentsAPI.assignCurator)

const gene: GeneRow = {
  assignment_id: 'a-1',
  gene_id: 'g-1',
  gene_symbol: 'BRCA1',
  gene_hgnc_id: 'HGNC:1100',
  curator_id: 'u-1',
  curator_name: 'Ada',
  priority: 'medium',
  assignment_notes: '',
  stage: 'precuration',
  due_date: null,
  updated_at: '2026-10-20T00:00:00Z'
}

const members = [
  { user_id: 'u-1', role: 'curator', user_full_name: 'Ada Lovelace', user_email: 'ada@x.org' },
  { user_id: 'u-2', role: 'curator', user_full_name: 'Grace Hopper', user_email: 'grace@x.org' },
  { user_id: 'u-3', role: 'viewer', user_full_name: 'Viewer', user_email: 'v@x.org' },
  { user_id: 'u-4', role: 'reviewer', user_full_name: 'Rev', user_email: 'r@x.org' }
]

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

/** Internal state read through wrapper.vm. */
interface ReassignVm {
  selectedCurator: { user_id: string } | null
  availableCurators: Array<{ user_id: string; displayName: string }>
  canSubmit: unknown
  handleSubmit(): Promise<void>
  handleCancel(): void
}

function internals(wrapper: { vm: unknown }): ReassignVm {
  return wrapper.vm as ReassignVm
}

// The modal loads curators when it opens (a watch on the open state), so mount closed first.
async function mountModal(props: Record<string, unknown> = {}) {
  const wrapper = mount(ReassignGeneModal, {
    props: { modelValue: false, scopeId: 'scope-1', gene, ...props },
    global: { stubs: { VDialog: dialogStub } }
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  return wrapper
}

describe('ReassignGeneModal', () => {
  beforeEach(() => {
    fetchMembers.mockReset()
    assignCurator.mockReset()
    addToast.mockReset()
    logger.error.mockReset()
    fetchMembers.mockResolvedValue(members)
  })

  it('shows the gene and its current curator', async () => {
    const wrapper = await mountModal()

    expect(wrapper.text()).toContain('BRCA1')
    expect(wrapper.text()).toContain('HGNC:1100')
    expect(wrapper.text()).toContain('Ada')
  })

  it('loads only curator-capable members of the scope when opened', async () => {
    const wrapper = await mountModal()

    expect(fetchMembers).toHaveBeenCalledWith('scope-1')
    expect(internals(wrapper).availableCurators.map(c => c.user_id)).toEqual(['u-1', 'u-2'])
    expect(internals(wrapper).availableCurators[0]?.displayName).toBe('Ada Lovelace')
  })

  it('logs and toasts when loading curators fails', async () => {
    fetchMembers.mockRejectedValue(new Error('forbidden'))

    await mountModal()

    expect(logger.error).toHaveBeenCalledWith('Failed to fetch curators', { error: 'forbidden' })
    expect(addToast).toHaveBeenCalledWith('Failed to load curators', 'error')
  })

  it('does not allow submitting when the chosen curator is already assigned', async () => {
    const wrapper = await mountModal()

    internals(wrapper).selectedCurator = { user_id: 'u-1' }
    await flushPromises()

    expect(internals(wrapper).canSubmit).toBeFalsy()
  })

  it('reassigns to the chosen curator, emits reassigned and closes', async () => {
    assignCurator.mockResolvedValue({} as never)
    const wrapper = await mountModal()

    internals(wrapper).selectedCurator = { user_id: 'u-2', full_name: 'Grace Hopper' } as never
    await flushPromises()
    await internals(wrapper).handleSubmit()

    expect(assignCurator).toHaveBeenCalledWith('a-1', 'u-2')
    expect(addToast).toHaveBeenCalledWith('BRCA1 reassigned to Grace Hopper', 'success')
    expect(wrapper.emitted('reassigned')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('reports a failed reassignment with the server detail', async () => {
    assignCurator.mockRejectedValue({ message: 'bad', response: { data: { detail: 'Locked' } } })
    const wrapper = await mountModal()

    internals(wrapper).selectedCurator = { user_id: 'u-2' }
    await flushPromises()
    await internals(wrapper).handleSubmit()

    expect(logger.error).toHaveBeenCalledWith('Failed to reassign gene', { error: 'bad' })
    expect(addToast).toHaveBeenCalledWith('Failed to reassign: Locked', 'error')
    expect(wrapper.emitted('reassigned')).toBeUndefined()
  })

  it('does nothing without a selected curator', async () => {
    const wrapper = await mountModal()

    await internals(wrapper).handleSubmit()

    expect(assignCurator).not.toHaveBeenCalled()
  })

  it('emits close on cancel', async () => {
    const wrapper = await mountModal()

    internals(wrapper).handleCancel()

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false])
  })
})
