import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CommandPalette from '../CommandPalette.vue'
import { searchAPI } from '@/api/search'
import { useSearchStore } from '@/stores/search'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/search', () => ({ searchAPI: { search: vi.fn() } }))

const push = vi.fn()
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
vi.mock('vue-router', () => ({ useRouter: () => ({ push, getRoutes: () => routes }) }))

const hits = {
  genes: [
    { id: 'g1', symbol: 'PKD1', hgnc_id: 'HGNC:9008' },
    { id: 'g2', symbol: 'PKD2', hgnc_id: 'HGNC:9009' }
  ],
  curations: [
    {
      id: 'c1',
      gene_symbol: 'PKD2',
      scope_id: 's1',
      scope_name: 'Kidney',
      status: 'changes_requested'
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
    ).toContain('changes requested')
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
    await click('changes requested')
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
