import { onBeforeUnmount, onMounted, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useConfirm } from '@/composables/useConfirm'

// Set when the user already chose to discard; the page reloads, so it never needs resetting
let discarding = false

/** Reload after the user chose to discard their changes (save conflict): no leave prompt. */
export function reloadDiscardingChanges() {
  discarding = true
  window.location.reload()
}

/** Asks before leaving the route and warns on tab close/reload while there are unsaved changes. */
export function useUnsavedGuard(dirty: Readonly<Ref<boolean>>) {
  const { confirm } = useConfirm()

  onBeforeRouteLeave(async () => {
    if (!dirty.value) return true
    return confirm({
      title: 'Leave without saving?',
      text: 'Your changes since the last save will be lost.',
      confirmText: 'Leave',
      destructive: true
    })
  })

  function onBeforeUnload(event: BeforeUnloadEvent) {
    if (!dirty.value || discarding) return
    event.preventDefault()
    event.returnValue = ''
  }
  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
}
