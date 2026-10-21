import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import GeneBulkBar from '../GeneBulkBar.vue'
import { assignmentsAPI } from '@/api'
import type { GeneRow } from '../types'

const addToast = vi.hoisted(() => vi.fn())
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/api', () => ({
  assignmentsAPI: { updateAssignment: vi.fn(), bulkAssignGenes: vi.fn() }
}))

const update = vi.mocked(assignmentsAPI.updateAssignment)
const rows = [{ assignment_id: 'a1' }, { assignment_id: 'a2' }] as GeneRow[]
const mountBar = (selected = rows) => {
  setActivePinia(createPinia())
  return mount(GeneBulkBar, {
    props: { selected },
    global: {
      stubs: { VMenu: { template: '<div><slot name="activator" :props="{}" /><slot /></div>' } }
    }
  })
}

describe('GeneBulkBar', () => {
  beforeEach(() => {
    update.mockReset()
    addToast.mockReset()
  })

  it('renders nothing without a selection', () => {
    expect(mountBar([]).find('[role=toolbar]').exists()).toBe(false)
  })

  it('shows the count and emits assign and clear', async () => {
    const w = mountBar()
    expect(w.text()).toContain('2 selected')
    await w.find('[data-testid=bulk-assign]').trigger('click')
    await w.find('[data-testid=bulk-clear]').trigger('click')
    expect(w.emitted('assign')).toHaveLength(1)
    expect(w.emitted('clear')).toHaveLength(1)
  })

  it('sets the priority on every selected assignment', async () => {
    update.mockResolvedValue({ priority: 'high', is_active: true } as never)
    const w = mountBar()
    await w.find('[data-testid=bulk-priority-high]').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith('a1', { priority_level: 'high' })
    expect(update).toHaveBeenCalledWith('a2', { priority_level: 'high' })
    expect(addToast).toHaveBeenCalledWith('Priority set to high for 2 genes', 'success')
    expect(w.emitted('changed')).toHaveLength(1)
  })

  it('sets the due date and reports partial failure', async () => {
    update
      .mockResolvedValueOnce({ priority: 'low', is_active: true } as never)
      .mockRejectedValueOnce(new Error('x'))
    const w = mountBar()
    await w.find('input[type=date]').setValue('2026-12-01')
    await w.find('[data-testid=bulk-due-apply]').trigger('click')
    await flushPromises()
    expect(update.mock.calls[0]![1]).toEqual({ due_date: new Date('2026-12-01').toISOString() })
    expect(addToast).toHaveBeenCalledWith('Due date set for 1 of 2 genes; 1 failed', 'error')
  })
})
