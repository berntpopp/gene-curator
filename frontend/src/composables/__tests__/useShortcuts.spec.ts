import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { effectScope } from 'vue'
import { useShortcuts } from '@/composables/useShortcuts'
import { useSearchStore } from '@/stores/search'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/search', () => ({ searchAPI: { search: vi.fn() } }))

const push = vi.fn()
vi.mock('@/components/navigation/useReviewBadge', () => ({ useReviewBadge: () => ({ value: 0 }) }))
const routes = [
  { name: 'Dashboard', meta: { showInMainMenu: true, requiresAuth: true, label: 'Dashboard' } },
  { name: 'GeneAssignments', meta: { showInMainMenu: true, requiresAuth: true, label: 'My work' } }
]
vi.mock('vue-router', () => ({ useRouter: () => ({ push, getRoutes: () => routes }) }))

const press = (key: string, opts: KeyboardEventInit = {}, target: EventTarget = document.body) => {
  const e = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...opts })
  target.dispatchEvent(e)
  return e
}

describe('useShortcuts', () => {
  let scope: ReturnType<typeof effectScope>
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    useAuthStore().isAuthenticated = true
    push.mockClear()
    scope = effectScope()
    scope.run(() => useShortcuts())
  })
  afterEach(() => {
    scope.stop()
    vi.useRealTimers()
    document.body.innerHTML = ''
  })

  it('Ctrl+K and Cmd+K open the palette anywhere, even inside an input', () => {
    const input = document.body.appendChild(document.createElement('input'))
    const e = press('k', { ctrlKey: true }, input)
    expect(useSearchStore().isOpen).toBe(true)
    expect(e.defaultPrevented).toBe(true)
    useSearchStore().close()
    press('k', { metaKey: true })
    expect(useSearchStore().isOpen).toBe(true)
  })

  it.each(['input', 'textarea', 'select'])('plain keys do nothing inside <%s>', tag => {
    const el = document.body.appendChild(document.createElement(tag))
    press('/', {}, el)
    press('?', {}, el)
    press('g', {}, el)
    press('w', {}, el)
    expect(useSearchStore().isOpen).toBe(false)
    expect(push).not.toHaveBeenCalled()
  })

  it('plain keys do nothing inside contenteditable', () => {
    const el = document.body.appendChild(document.createElement('div'))
    el.setAttribute('contenteditable', 'true')
    Object.defineProperty(el, 'isContentEditable', { value: true })
    press('/', {}, el)
    expect(useSearchStore().isOpen).toBe(false)
  })

  it('"/" opens the palette and "?" opens it on the shortcut list', () => {
    const e = press('/')
    expect(useSearchStore().isOpen).toBe(true)
    expect(useSearchStore().showHelp).toBe(false)
    expect(e.defaultPrevented).toBe(true) // the slash must not land in the focused input
    useSearchStore().close()
    press('?', { shiftKey: true })
    expect(useSearchStore().showHelp).toBe(true)
  })

  it('"g" then "w" goes to My work; a lone "w" or a late "w" does not', () => {
    press('w')
    expect(push).not.toHaveBeenCalled()
    press('g')
    press('w')
    // the target is the rail's "My work" entry, not a hardcoded route name
    expect(push).toHaveBeenCalledWith({ name: 'GeneAssignments' })
    push.mockClear()
    press('g')
    vi.advanceTimersByTime(1500)
    press('w')
    expect(push).not.toHaveBeenCalled()
  })

  it('ignores modified keys other than Ctrl/Cmd+K and everything when signed out', () => {
    press('/', { ctrlKey: true })
    press('g', { altKey: true })
    expect(useSearchStore().isOpen).toBe(false)
    useAuthStore().isAuthenticated = false
    press('k', { ctrlKey: true })
    press('/')
    expect(useSearchStore().isOpen).toBe(false)
  })

  it('stops listening when its scope is disposed', () => {
    scope.stop()
    press('k', { ctrlKey: true })
    expect(useSearchStore().isOpen).toBe(false)
  })
})
