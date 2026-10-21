import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Ctrl/Cmd+S saves, also while typing in a field (the browser's save-page dialog is suppressed).
 * Inside a dialog the shortcut is left alone: the dialog owns the keyboard.
 */
export function useSaveShortcut(save: () => unknown, enabled: () => boolean = () => true) {
  function onKeydown(event: KeyboardEvent) {
    if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey) return
    if (event.key.toLowerCase() !== 's') return
    // Never let the browser open its save-page dialog, whatever the checks below decide
    event.preventDefault()
    if (event.repeat || !enabled()) return
    if ((event.target as Element | null)?.closest?.('[role="dialog"], [aria-modal="true"]')) return
    save()
  }
  onMounted(() => document.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
}
