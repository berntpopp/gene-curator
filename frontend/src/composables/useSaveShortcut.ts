import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Ctrl/Cmd+S saves, also while typing in a field (the browser's save-page dialog is suppressed).
 * Inside a dialog the shortcut is left alone: the dialog owns the keyboard.
 */
export function useSaveShortcut(save: () => unknown, enabled: () => boolean = () => true) {
  function onKeydown(event: KeyboardEvent) {
    if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey || event.repeat) return
    if (event.key.toLowerCase() !== 's' || !enabled()) return
    if ((event.target as Element | null)?.closest?.('[role="dialog"], [aria-modal="true"]')) return
    event.preventDefault()
    save()
  }
  onMounted(() => document.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
}
