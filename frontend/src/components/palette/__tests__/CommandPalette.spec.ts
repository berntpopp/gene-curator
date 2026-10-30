import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CommandPalette from '../CommandPalette.vue'
import { searchAPI } from '@/api/search'
import { useSearchStore } from '@/stores/search'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/search', () => ({ searchAPI: { search: vi.fn() } }))

const push = vi.fn()
vi.mock('@/components/navigation/useReviewBadge', () => ({ useReviewBadge: () => ({ value: 0 }) }))
const routes = [
  {
    name: 'Dashboard',
    meta: { showInMainMenu: true, requiresAuth: true, label: 'My work', order: 1 }
  },
  { name: 'GeneCatalogue', meta: { showInMainMenu: true, label: 'Gene Catalogue', order: 4 } },
  {
    name: 'admin-users',
    meta: {
      showInDropdown: 'curationSetup',
      requiresAuth: true,
      requiredRoles: ['admin'],
      label: 'Users',
      order: 9
    }
  },
  { name: 'Login', meta: { requiresGuest: true, showInMainMenu: true, label: 'Sign in' } }
]
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, getRoutes: () => routes, afterEach: () => () => undefined })
}))

const hits = {
  genes: [
    { id: 'g1', symbol: 'PKD1', hgnc_id: 'HGNC:9008', classification: 'definitive' },
    { id: 'g2', symbol: 'PKD2', hgnc_id: 'HGNC:9009' }
  ],
  curations: [
    {
      id: 'c1',
      gene_symbol: 'PKD2',
      scope_id: 's1',
      scope_name: 'Kidney',
      status: 'in_review',
      disease_name: 'Polycystic kidney disease 2',
      mode_of_inheritance: 'AD'
    }
  ],
  scopes: [{ id: 's1', name: 'kidney', display_name: 'Kidney genetics' }]
}

describe('CommandPalette', () => {
  let wrapper: VueWrapper
  let trigger: HTMLButtonElement
  const q = (sel: string) => document.body.querySelector<HTMLElement>(sel)
  const input = () => q('input[role="combobox"]') as HTMLInputElement
  const key = async (k: string) => {
    input().dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }))
    await flushPromises()
  }
  const type = async (text: string) => {
    input().value = text
    input().dispatchEvent(new Event('input', { bubbles: true }))
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
  }
  const options = () => [...document.body.querySelectorAll<HTMLElement>('[role="option"]')]

  beforeEach(async () => {
    vi.useFakeTimers()
    const pinia = createPinia()
    setActivePinia(pinia)
    useAuthStore().isAuthenticated = true
    useAuthStore().user = { id: 'u', role: 'user' } as never
    push.mockClear()
    vi.mocked(searchAPI.search).mockReset()
    vi.mocked(searchAPI.search).mockResolvedValue(hits as never)
    trigger = document.body.appendChild(document.createElement('button'))
    trigger.focus()
    wrapper = mount(CommandPalette, { attachTo: document.body, global: { plugins: [pinia] } })
    useSearchStore().open()
    await flushPromises()
  })
  afterEach(() => {
    wrapper.unmount()
    vi.useRealTimers()
    document.body.innerHTML = ''
  })

  it('is a labelled combobox over a listbox and focuses the field', () => {
    expect(document.activeElement).toBe(input())
    expect(input().getAttribute('aria-expanded')).toBe('true')
    expect(input().getAttribute('aria-controls')).toBe(q('[role="listbox"]')!.id)
    expect(input().getAttribute('aria-label')).toBeTruthy()
  })

  it('lists navigation commands from route meta, honouring role gating', () => {
    const labels = options().map(o => o.textContent)
    expect(labels.join('|')).toContain('My work')
    expect(labels.join('|')).toContain('Gene Catalogue')
    expect(labels.join('|')).not.toContain('Users') // admin only
    expect(labels.join('|')).not.toContain('Sign in') // guests only
  })

  it('shows admin entries to admins', async () => {
    useAuthStore().user = { id: 'u', role: 'admin' } as never
    await flushPromises()
    expect(
      options()
        .map(o => o.textContent)
        .join('|')
    ).toContain('Users')
  })

  it('shows the classification of a gene hit when it has one (#273)', async () => {
    await type('pkd')
    const genes = options().filter(o => o.textContent?.includes('HGNC:'))
    expect(genes[0]!.textContent).toContain('Definitive')
    expect(genes[1]!.textContent).not.toContain('classified')
  })

  it('names the disease and MOI of a curation hit (#530)', async () => {
    await type('pkd')
    const [hit] = options().filter(o => o.textContent?.includes('PKD2 curation'))
    expect(hit!.textContent).toContain('Polycystic kidney disease 2 · Autosomal dominant · Kidney')
  })

  it('debounces typing into one request and renders grouped results', async () => {
    await type('pkd')
    expect(searchAPI.search).toHaveBeenCalledTimes(1)
    const groups = [...document.body.querySelectorAll('[role="group"]')].map(g =>
      g.getAttribute('aria-label')
    )
    expect(groups).toEqual(expect.arrayContaining(['Genes', 'Curations', 'Scopes']))
    expect(
      options()
        .map(o => o.textContent)
        .join('|')
    ).toContain('PKD1')
    expect(
      options()
        .map(o => o.textContent)
        .join('|')
    ).toContain('In review')
  })

  it('colours the curation status chip from config/status.ts', async () => {
    await type('pkd')
    const chip = options()
      .find(o => o.textContent!.includes('PKD2 curation'))!
      .querySelector('.v-chip')
    expect(chip?.textContent).toContain('In review')
    expect(chip?.className).toContain('text-warning')
  })

  it('moves with the arrow keys (wrapping), tracked by aria-activedescendant', async () => {
    await type('pkd')
    const opts = options()
    expect(opts[0]!.getAttribute('aria-selected')).toBe('true')
    await key('ArrowDown')
    expect(input().getAttribute('aria-activedescendant')).toBe(opts[1]!.id)
    await key('ArrowUp')
    await key('ArrowUp')
    expect(input().getAttribute('aria-activedescendant')).toBe(opts.at(-1)!.id)
  })

  it('Enter on a typed symbol opens the gene page and closes the palette', async () => {
    await type('PKD1')
    await key('Enter')
    expect(push).toHaveBeenCalledWith({ name: 'GeneDetail', params: { id: 'g1' } })
    expect(useSearchStore().isOpen).toBe(false)
  })

  it('Enter pressed before the results arrive opens the first result once they do', async () => {
    input().value = 'PKD1'
    input().dispatchEvent(new Event('input', { bubbles: true }))
    await key('Enter') // still debouncing: nothing to open yet
    expect(push).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    expect(push).toHaveBeenCalledWith({ name: 'GeneDetail', params: { id: 'g1' } })
    expect(useSearchStore().isOpen).toBe(false)
  })

  it('drops a waiting Enter when the query changes or nothing is found', async () => {
    input().value = 'PKD1'
    input().dispatchEvent(new Event('input', { bubbles: true }))
    await key('Enter')
    await type('PKD2') // typing on cancels the pending open
    expect(push).not.toHaveBeenCalled()
    vi.mocked(searchAPI.search).mockResolvedValue({ genes: [], curations: [], scopes: [] } as never)
    input().value = 'zzzz'
    input().dispatchEvent(new Event('input', { bubbles: true }))
    await key('Enter')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    expect(push).not.toHaveBeenCalled()
    expect(useSearchStore().isOpen).toBe(true)
  })

  it('opens curations and scopes by their routes', async () => {
    await type('pkd')
    const click = async (text: string) => {
      options()
        .find(o => o.textContent!.includes(text))!
        .click()
      await flushPromises()
      useSearchStore().open()
      await flushPromises()
      await type('pkd')
    }
    await click('Kidney genetics')
    expect(push).toHaveBeenLastCalledWith({ name: 'scope-dashboard', params: { scopeId: 's1' } })
    await click('In review')
    expect(push).toHaveBeenLastCalledWith({
      name: 'curation-detail',
      params: { scopeId: 's1', curationId: 'c1' }
    })
  })

  it('Esc closes and focus returns to where it was', async () => {
    useSearchStore().close()
    await flushPromises()
    trigger.focus()
    useSearchStore().open()
    await flushPromises()
    expect(document.activeElement).toBe(input())
    useSearchStore().close()
    await flushPromises()
    await vi.advanceTimersByTimeAsync(300)
    expect(document.activeElement).toBe(trigger)
  })

  it('Escape in the field closes the palette', async () => {
    await key('Escape')
    await vi.advanceTimersByTimeAsync(300)
    expect(useSearchStore().isOpen).toBe(false)
  })

  it('Tab stays inside the dialog (focus trap)', async () => {
    const dialog = q('[role="dialog"]')!
    const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    input().dispatchEvent(tab)
    await flushPromises()
    expect(dialog.contains(document.activeElement) || tab.defaultPrevented).toBe(true)
  })

  it('says so when nothing matches and when the search failed', async () => {
    vi.mocked(searchAPI.search).mockResolvedValueOnce({
      genes: [],
      curations: [],
      scopes: []
    } as never)
    await type('zzzz')
    expect(document.body.textContent).toContain('No results for')
    vi.mocked(searchAPI.search).mockRejectedValueOnce(new Error('x'))
    await type('zzzzz')
    expect(q('[role="alert"]')!.textContent).toContain('Search failed')
  })

  it('shows only the error, never also "No results", when the search failed', async () => {
    vi.mocked(searchAPI.search).mockRejectedValueOnce({ response: { status: 422 } })
    await type('a\u0000b')
    expect(q('[role="alert"]')!.textContent).toContain('Search failed')
    expect(document.body.textContent).not.toContain('No results for')
  })

  it('shows the shortcut list for "?"', async () => {
    useSearchStore().close()
    await flushPromises()
    useSearchStore().open({ help: true })
    await flushPromises()
    expect(document.body.textContent).toContain('Go to My work')
    expect(document.body.textContent).toContain('Open the command palette')
  })

  it('pressing a number of chars shorter than 2 does not search', async () => {
    await type('p')
    expect(searchAPI.search).not.toHaveBeenCalled()
  })
})
