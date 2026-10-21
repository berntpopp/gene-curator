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
const rows = [
  { assignment_id: 'a1', gene_id: 'g1', gene_symbol: 'AAA', curator_id: null },
  { assignment_id: 'a2', gene_id: 'g2', gene_symbol: 'BBB', curator_id: null }
] as GeneRow[]
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
    expect(w.emitted('changed')![0]).toEqual([[]])
  })

  it('has no due date action (assignment summaries carry no due date to show)', () => {
    expect(mountBar().find('[data-testid=bulk-due]').exists()).toBe(false)
  })

  it('names the failed genes and keeps only them selected', async () => {
    update
      .mockResolvedValueOnce({ priority: 'low', is_active: true } as never)
      .mockRejectedValueOnce(new Error('x'))
    const w = mountBar()
    await w.find('[data-testid=bulk-priority-low]').trigger('click')
    await flushPromises()
    expect(addToast).toHaveBeenCalledWith(
      'Priority set to low for 1 of 2 genes. Failed: BBB',
      'error'
    )
    expect(w.emitted('changed')![0]).toEqual([['g2']])
  })

  it('sends updates in batches of five', async () => {
    let running = 0
    let peak = 0
    update.mockImplementation(async () => {
      peak = Math.max(peak, ++running)
      await new Promise(r => setTimeout(r, 1))
      running--
      return { priority: 'low', is_active: true } as never
    })
    const many = Array.from({ length: 12 }, (_, i) => ({
      assignment_id: `a${i}`,
      gene_id: `g${i}`,
      gene_symbol: `G${i}`,
      curator_id: null
    })) as GeneRow[]
    const w = mountBar(many)
    await w.find('[data-testid=bulk-priority-low]').trigger('click')
    await vi.waitFor(() => expect(update).toHaveBeenCalledTimes(12))
    await flushPromises()
    expect(peak).toBe(5)
  })

  it('ignores a second click while a run is in progress', async () => {
    let release!: () => void
    update.mockImplementation(
      () => new Promise(r => (release = () => r({ priority: 'low', is_active: true } as never)))
    )
    const w = mountBar([rows[0]!])
    await w.find('[data-testid=bulk-priority-low]').trigger('click')
    await w.find('[data-testid=bulk-priority-low]').trigger('click')
    expect(update).toHaveBeenCalledTimes(1)
    expect(w.find('[data-testid=bulk-assign]').attributes('disabled')).toBeDefined()
    release()
    await flushPromises()
    expect(w.find('[data-testid=bulk-assign]').attributes('disabled')).toBeUndefined()
  })

  it('tells how many selected genes already have a curator and disables assign when none can be', async () => {
    const mixed = [
      { ...rows[0]!, curator_id: 'u1' },
      { ...rows[1]!, curator_id: 'u2' },
      { assignment_id: 'a3', gene_id: 'g3', gene_symbol: 'CCC', curator_id: null }
    ] as GeneRow[]
    const w = mountBar(mixed)
    expect(w.find('[data-testid=bulk-skipped]').text()).toBe('2 already have a curator')
    expect(w.find('[data-testid=bulk-assign]').attributes('disabled')).toBeUndefined()

    const all = mountBar([mixed[0]!])
    expect(all.find('[data-testid=bulk-assign]').attributes('disabled')).toBeDefined()
    expect(all.find('[data-testid=bulk-skipped]').text()).toBe('1 already has a curator')
  })
})
