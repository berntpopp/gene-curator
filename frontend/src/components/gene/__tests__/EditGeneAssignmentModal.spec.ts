import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EditGeneAssignmentModal from '../EditGeneAssignmentModal.vue'
import { assignmentsAPI, genesAPI } from '@/api'
import type { GeneRow } from '../types'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/api', () => ({
  assignmentsAPI: { updateAssignment: vi.fn() },
  genesAPI: { validateGene: vi.fn() }
}))

const updateAssignment = vi.mocked(assignmentsAPI.updateAssignment)
const validateGene = vi.mocked(genesAPI.validateGene)

const gene: GeneRow = {
  assignment_id: 'a-1',
  gene_id: 'g-1',
  gene_symbol: 'BRCA1',
  gene_name: '',
  gene_hgnc_id: '',
  curator_id: 'u-1',
  curator_name: 'Ada',
  priority: 'normal',
  assignment_notes: 'old note',
  status: 'assigned',
  due_date: '2025-06-01T00:00:00Z',
  progress: 0
}

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

/** Internal state read through wrapper.vm. */
interface EditVm {
  formData: { priority: string; due_date: string | null; assignment_notes: string }
  hasChanges: boolean
  validationResult: { is_valid: boolean } | null
  handleSubmit(): Promise<void>
  handleRevalidateGene(): Promise<void>
}

function internals(wrapper: { vm: unknown }): EditVm {
  return wrapper.vm as EditVm
}

// The form initialises when the modal opens (a watch on the open state), so mount closed first.
async function mountModal(props: Record<string, unknown> = {}) {
  const wrapper = mount(EditGeneAssignmentModal, {
    props: { modelValue: false, scopeId: 'scope-1', gene, ...props },
    global: { stubs: { VDialog: dialogStub } }
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  return wrapper
}

describe('EditGeneAssignmentModal', () => {
  beforeEach(() => {
    updateAssignment.mockReset()
    validateGene.mockReset()
    addToast.mockReset()
    logger.error.mockReset()
  })

  it('initialises the form from the gene, mapping normal to medium', async () => {
    const wrapper = await mountModal()

    expect(internals(wrapper).formData).toEqual({
      priority: 'medium',
      due_date: '2025-06-01',
      assignment_notes: 'old note'
    })
    expect(internals(wrapper).hasChanges).toBe(false)
  })

  it('tracks changes against the original values', async () => {
    const wrapper = await mountModal()

    internals(wrapper).formData.assignment_notes = 'new note'
    await flushPromises()

    expect(internals(wrapper).hasChanges).toBe(true)
  })

  it('saves changed values with the API priority and ISO due date', async () => {
    updateAssignment.mockResolvedValue({} as never)
    const wrapper = await mountModal()

    internals(wrapper).formData.priority = 'high'
    internals(wrapper).formData.assignment_notes = ''
    await flushPromises()
    await internals(wrapper).handleSubmit()

    expect(updateAssignment).toHaveBeenCalledWith('a-1', {
      priority_level: 'high',
      assignment_notes: null,
      due_date: new Date('2025-06-01').toISOString()
    })
    expect(addToast).toHaveBeenCalledWith('BRCA1 assignment updated', 'success')
    expect(wrapper.emitted('updated')).toHaveLength(1)
  })

  it('clears the due date when it is removed', async () => {
    updateAssignment.mockResolvedValue({} as never)
    const wrapper = await mountModal()

    internals(wrapper).formData.due_date = null
    await flushPromises()
    await internals(wrapper).handleSubmit()

    expect(updateAssignment).toHaveBeenCalledWith(
      'a-1',
      expect.objectContaining({ due_date: null })
    )
  })

  it('does not save when nothing changed', async () => {
    const wrapper = await mountModal()

    await internals(wrapper).handleSubmit()

    expect(updateAssignment).not.toHaveBeenCalled()
  })

  it('reports a failed save with the server detail', async () => {
    updateAssignment.mockRejectedValue({ message: 'x', response: { data: { detail: 'Conflict' } } })
    const wrapper = await mountModal()

    internals(wrapper).formData.assignment_notes = 'changed'
    await flushPromises()
    await internals(wrapper).handleSubmit()

    expect(addToast).toHaveBeenCalledWith('Failed to update: Conflict', 'error')
    expect(logger.error).toHaveBeenCalledWith('Failed to update assignment', { error: 'x' })
  })

  it('revalidates the gene and reports valid and invalid results', async () => {
    validateGene.mockResolvedValueOnce({ is_valid: true, approved_symbol: 'BRCA1' } as never)
    const wrapper = await mountModal()

    await internals(wrapper).handleRevalidateGene()
    expect(validateGene).toHaveBeenCalledWith('g-1')
    expect(addToast).toHaveBeenCalledWith('BRCA1 annotation is valid', 'success')
    expect(wrapper.emitted('revalidated')?.[0]).toEqual([
      { is_valid: true, approved_symbol: 'BRCA1' }
    ])

    validateGene.mockResolvedValueOnce({ is_valid: false, warnings: ['old symbol'] } as never)
    await internals(wrapper).handleRevalidateGene()
    expect(addToast).toHaveBeenCalledWith('BRCA1 has validation warnings', 'warning')
    expect(internals(wrapper).validationResult).toEqual({
      is_valid: false,
      warnings: ['old symbol']
    })
  })

  it('reports a failed revalidation', async () => {
    validateGene.mockRejectedValue({ message: 'down', response: { data: { detail: 'Upstream' } } })
    const wrapper = await mountModal()

    await internals(wrapper).handleRevalidateGene()

    expect(addToast).toHaveBeenCalledWith('Failed to revalidate: Upstream', 'error')
  })

  it('does not revalidate a gene without an id', async () => {
    const wrapper = await mountModal({ gene: { ...gene, gene_id: '' } })

    await internals(wrapper).handleRevalidateGene()

    expect(validateGene).not.toHaveBeenCalled()
  })

  it('treats a missing priority as medium and an empty date as none', async () => {
    const wrapper = await mountModal({
      gene: { ...gene, priority: undefined, due_date: null, assignment_notes: '' }
    })

    expect(internals(wrapper).formData).toEqual({
      priority: 'medium',
      due_date: null,
      assignment_notes: ''
    })
  })
})
