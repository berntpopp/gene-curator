import { describe, it, expect, vi, beforeEach, type MockInstance } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { useMyWorkStore } from '@/stores/myWork'
import MyWork from '@/views/MyWork.vue'
import type { Schema } from '@/types/api'

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

let router: Router
let push: MockInstance<Router['push']>

async function newRouter(url = '/my-work') {
  router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }]
  })
  await router.push(url)
  push = vi.spyOn(router, 'push')
}

function mountView(items: Schema<'WorkItem'>[]) {
  const store = useMyWorkStore()
  vi.spyOn(store, 'fetchMyWork').mockResolvedValue(undefined)
  store.items = items
  store.counts = { needs_you: 2, waiting: 1, done: 0 }
  return mount(MyWork, {
    global: { plugins: [router], stubs: { RouterLink: RouterLinkStub, PendingInvitations: true } }
  })
}

// Router install starts a navigation of its own; let it finish before the table writes the URL
const settle = async () => {
  await flushPromises()
  await new Promise(r => setTimeout(r))
  await flushPromises()
}

const rows = (w: ReturnType<typeof mountView>) => w.findAll('[data-test="work-row"]')

describe('MyWork view', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    await newRouter()
  })

  it('loads on mount, shows tab counts and the needs-you rows with deep links from the API', async () => {
    const w = mountView([
      item({}),
      item({ item_id: 'i2', gene_symbol: 'PKD2', verb: 'Answer 2 review comments', link: '/x/2' }),
      item({ item_id: 'i3', tab: 'waiting', gene_symbol: 'HNF1B' })
    ])
    await settle()
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
    await settle()
    expect(rows(w)[0]!.text()).toContain('2d ago')
  })

  it('shows disease, inheritance, stage and classification on each row (#277)', async () => {
    const w = mountView([
      item({
        disease_name: 'Nephrotic syndrome',
        mode_of_inheritance: 'AR',
        stage: 'curation',
        classification: 'moderate'
      }),
      item({ item_id: 'i2' })
    ])
    await settle()
    const [full, bare] = rows(w)
    expect(full!.text()).toContain('Nephrotic syndrome')
    expect(full!.text()).toContain('Autosomal recessive')
    expect(full!.text()).toContain('Curation')
    expect(full!.text()).toContain('Moderate')
    expect(bare!.text()).not.toContain('Not classified')
  })

  it('keeps rows of one next action together, in API order', async () => {
    const w = mountView([
      item({}),
      item({ item_id: 'i2', verb: 'Review curation', gene_symbol: 'PKD1' }),
      item({ item_id: 'i3', gene_symbol: 'HNF1B' })
    ])
    await settle()
    expect(rows(w).map(r => r.text())).toEqual([
      expect.stringContaining('Start precuration'),
      expect.stringContaining('Start precuration'),
      expect.stringContaining('Review curation')
    ])
    expect(rows(w)[1]!.text()).toContain('HNF1B')
  })

  it('shows the total in the table footer and keeps the tab in the URL', async () => {
    const w = mountView([item({}), item({ item_id: 'i2' })])
    await settle()
    expect(w.text()).toContain('1-2 of 2')
    await w.findAll('[role="tab"]')[1]!.trigger('click')
    await settle()
    expect(router.currentRoute.value.query.tab).toBe('waiting')
  })

  it('opens on the tab named in the URL', async () => {
    await newRouter('/my-work?tab=waiting')
    const w = mountView([item({}), item({ item_id: 'i3', tab: 'waiting', gene_symbol: 'HNF1B' })])
    await settle()
    expect(rows(w).map(r => r.text())).toEqual([expect.stringContaining('HNF1B')])
  })

  it('marks the J/K row as current', async () => {
    const w = mountView([item({}), item({ item_id: 'i2' })])
    await settle()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }))
    await settle()
    expect(rows(w).map(r => r.attributes('aria-current'))).toEqual([undefined, 'true'])
    w.unmount()
  })

  it('switches tabs and shows a per-tab empty state', async () => {
    const w = mountView([item({})])
    await settle()
    await w.findAll('[role="tab"]')[2]!.trigger('click')
    await settle()
    expect(w.text()).toContain('Nothing finished this week')
  })

  it('moves with J and K and opens the row with Enter', async () => {
    const w = mountView([item({}), item({ item_id: 'i2', link: '/second' })])
    await settle()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }))
    await settle()
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
    await settle()
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
    await settle()
    expect(w.findAll('[role="tab"]').map(t => t.text())).toEqual([
      'Needs you 2',
      'Waiting 1',
      'Done 0'
    ])
    expect(w.find('kbd').element.parentElement!.classList).toContain('d-none')
  })

  it('ignores shortcuts typed into the filter field', async () => {
    const w = mountView([item({})])
    await settle()
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
    await settle()
    await w.find('input').setValue('pkd')
    await new Promise(r => setTimeout(r, 350)) // the search reaches the URL debounced
    await settle()
    expect(router.currentRoute.value.query.q).toBe('pkd')
    expect(rows(w)).toHaveLength(1)
  })

  it('says no matches, not "nothing needs you", when a search finds nothing', async () => {
    const w = mountView([item({})])
    await settle()
    await w.find('input').setValue('zzz')
    await settle()
    expect(w.text()).toContain('No work matches the search.')
    expect(w.text()).not.toContain('Nothing needs you')
  })

  it('shows the store error with a retry', async () => {
    const w = mountView([])
    useMyWorkStore().error = 'Request failed'
    await settle()
    expect(w.text()).toContain('Request failed')
    await w.find('[data-testid="table-retry"]').trigger('click')
    expect(useMyWorkStore().fetchMyWork).toHaveBeenCalledTimes(2)
  })
})
