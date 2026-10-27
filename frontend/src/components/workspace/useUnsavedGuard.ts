import { onBeforeUnmount, onMounted, type Ref } from 'vue'
import { onBeforeRouteLeave, type RouteLocationRaw, type Router } from 'vue-router'
import { useConfirm } from '@/composables/useConfirm'

// Set when the user already chose to discard; the page reloads, so it never needs resetting
let discarding = false

/** Reload after the user chose to discard their changes (save conflict): no leave prompt. */
export function reloadDiscardingChanges() {
  discarding = true
  window.location.reload()
}

// A focused cell commits its typed text on blur, which is what makes the page dirty (#469)
const commitFocused = () => (document.activeElement as HTMLElement | null)?.blur?.()

// Set while the URL moves to another address of the same document
let keeping = false

/** Changes the URL without the leave prompt, e.g. /new -> the edit page of the curation just created. */
export async function replaceKeepingChanges(router: Router, to: RouteLocationRaw) {
  keeping = true
  try {
    await router.replace(to)
  } finally {
    keeping = false
  }
}

/** Asks before leaving the route and warns on tab close/reload while there are unsaved changes. */
export function useUnsavedGuard(dirty: Readonly<Ref<boolean>>) {
  const { confirm } = useConfirm()

  onBeforeRouteLeave(async () => {
    commitFocused()
    if (!dirty.value || keeping) return true
    return confirm({
      title: 'Leave without saving?',
      text: 'Your changes since the last save will be lost.',
      confirmText: 'Leave',
      destructive: true
    })
  })

  function onBeforeUnload(event: BeforeUnloadEvent) {
    commitFocused()
    if (!dirty.value || discarding) return
    event.preventDefault()
    event.returnValue = ''
  }
  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
}
