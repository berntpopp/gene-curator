import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useMyWorkStore } from '@/stores/myWork'
import MyWork from '@/views/MyWork.vue'
import type { Schema } from '@/types/api'

const push = vi.hoisted(() => vi.fn())
vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push })
}))
vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const item = (over: Partial<Schema<'WorkItem'>>): Schema<'WorkItem'> => ({
  kind: 'assignment',
  tab: 'needs_you',
  verb: 'Start precuration',
  item_type: 'assignment',
  item_id: 'i1',
  gene_id: 'g1',
  gene_symbol: 'NPHS2',
  scope_id: 's1',
  scope_name: 'Kidney genetics',
  link: '/assignments/i1',
  updated_at: '2026-10-20T10:00:00Z',
  ...over
})

function mountView(items: Schema<'WorkItem'>[]) {
  const store = useMyWorkStore()
  vi.spyOn(store, 'fetchMyWork').mockResolvedValue(undefined)
  store.items = items
  store.counts = { needs_you: 2, waiting: 1, done: 0 }
  return mount(MyWork, {
    global: { stubs: { RouterLink: RouterLinkStub, PendingInvitations: true } }
  })
}

const rows = (w: ReturnType<typeof mountView>) => w.findAll('[data-test="work-row"]')

describe('MyWork view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
  })

  it('loads on mount, shows tab counts and the needs-you rows with deep links from the API', async () => {
    const w = mountView([
      item({}),
      item({ item_id: 'i2', gene_symbol: 'PKD2', verb: 'Answer 2 review comments', link: '/x/2' }),
      item({ item_id: 'i3', tab: 'waiting', gene_symbol: 'HNF1B' })
    ])
    await flushPromises()
    expect(useMyWorkStore().fetchMyWork).toHaveBeenCalled()
    expect(w.text()).toContain('Needs you')
    expect(rows(w)).toHaveLength(2)
    expect(w.text()).not.toContain('HNF1B')
    const links = w.findAllComponents({ name: 'VBtn' }).map(l => l.props('to'))
    expect(links).toContain('/x/2')
  })

  it('shows how long each row has waited', async () => {
    const twoDays = new Date(Date.now() - 2 * 86_400_000).toISOString()
    const w = mountView([item({ updated_at: twoDays })])
    await flushPromises()
    expect(rows(w)[0]!.text()).toContain('2d ago')
  })

  it('groups rows by next action', async () => {
    const w = mountView([item({}), item({ item_id: 'i2', verb: 'Review curation' })])
    await flushPromises()
    expect(w.findAll('[data-test="work-group"]').map(g => g.text())).toEqual([
      expect.stringContaining('Start precuration'),
      expect.stringContaining('Review curation')
    ])
  })

  it('switches tabs and shows a per-tab empty state', async () => {
    const w = mountView([item({})])
    await flushPromises()
    await w.findAll('[role="tab"]')[2]!.trigger('click')
    expect(w.text()).toContain('Nothing finished this week')
  })

  it('moves with J and K and opens the row with Enter', async () => {
    const w = mountView([item({}), item({ item_id: 'i2', link: '/second' })])
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }))
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    expect(push).toHaveBeenCalledWith('/second')
    w.unmount()
  })

  it('ignores J when the key event is already handled or carries Alt', async () => {
    const w = mountView([
      item({}),
      item({ item_id: 'i2', link: '/second' }),
      item({ item_id: 'i3', link: '/third' })
    ])
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', altKey: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', cancelable: true }))
    const handled = new KeyboardEvent('keydown', { key: 'j', cancelable: true })
    window.addEventListener('keydown', e => e.preventDefault(), { once: true, capture: true })
    window.dispatchEvent(handled)
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    expect(push).toHaveBeenCalledWith('/second') // only the unhandled J moved
    w.unmount()
  })

  it('uses short pill labels on the tabs and hides the keyboard hint below md', async () => {
    const w = mountView([item({})])
    await flushPromises()
    expect(w.findAll('[role="tab"]').map(t => t.text())).toEqual([
      'Needs you 2',
      'Waiting 1',
      'Done 0'
    ])
    expect(w.find('kbd').element.parentElement!.classList).toContain('d-none')
  })

  it('ignores shortcuts typed into the filter field', async () => {
    const w = mountView([item({})])
    await flushPromises()
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', bubbles: true }))
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    expect(push).not.toHaveBeenCalled()
    input.remove()
    w.unmount()
  })

  it('filters by gene symbol', async () => {
    const w = mountView([item({}), item({ item_id: 'i2', gene_symbol: 'PKD2' })])
    await flushPromises()
    await w.find('input').setValue('pkd')
    expect(rows(w)).toHaveLength(1)
  })

  it('shows the store error with a retry', async () => {
    const w = mountView([])
    useMyWorkStore().error = 'Request failed'
    await flushPromises()
    expect(w.text()).toContain('Request failed')
    await w.find('.retry').trigger('click')
    expect(useMyWorkStore().fetchMyWork).toHaveBeenCalledTimes(2)
  })
})
