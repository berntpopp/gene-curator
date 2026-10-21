import { onScopeDispose } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSearchStore } from '@/stores/search'

export interface ShortcutInfo {
  keys: string[]
  label: string
}

/** Shown by "?" in the palette; keep in step with the handler below. */
export const SHORTCUTS: ShortcutInfo[] = [
  { keys: ['Ctrl', 'K'], label: 'Open the command palette' },
  { keys: ['/'], label: 'Search genes, curations and scopes' },
  { keys: ['G', 'W'], label: 'Go to My work' },
  { keys: ['?'], label: 'Show all shortcuts' },
  { keys: ['Esc'], label: 'Close the palette' }
]

const SEQUENCE_MS = 1000

const isTyping = (t: EventTarget | null) => {
  const el = t as HTMLElement | null
  return !!el && (['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || el.isContentEditable)
}

/** Global keyboard shortcuts. Call once (App-level); the listener goes away with the scope. */
export function useShortcuts() {
  const router = useRouter()
  const auth = useAuthStore()
  const search = useSearchStore()
  let gAt = 0

  function onKeydown(e: KeyboardEvent) {
    if (!auth.isAuthenticated || e.defaultPrevented) return

    // Ctrl/Cmd+K works everywhere, inputs included.
    if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === 'k') {
      e.preventDefault()
      search.open()
      return
    }
    // Everything else is a bare key and must never fire while typing or inside the palette.
    if (e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target) || search.isOpen) return

    if (e.key === '/') {
      e.preventDefault()
      search.open()
    } else if (e.key === '?') {
      e.preventDefault()
      search.open({ help: true })
    } else if (e.key.toLowerCase() === 'g') {
      gAt = Date.now()
    } else if (e.key.toLowerCase() === 'w' && Date.now() - gAt < SEQUENCE_MS) {
      gAt = 0
      void router.push({ name: 'Dashboard' })
    }
  }

  window.addEventListener('keydown', onKeydown)
  onScopeDispose(() => window.removeEventListener('keydown', onKeydown))
}
