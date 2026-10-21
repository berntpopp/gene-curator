import { watch, type Ref } from 'vue'

function hasRows(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0
  if (value && typeof value === 'object') return Object.values(value).some(hasRows)
  return false
}

/** Open each panel the moment it gains rows (mount, restore); never re-open one the user closed. */
export function openPanelsWithRows(
  expanded: Ref<string[]>,
  groups: () => Record<string, unknown>
): void {
  watch(
    () => Object.fromEntries(Object.entries(groups()).map(([k, v]) => [k, hasRows(v)])),
    (now, before) => {
      for (const [panel, filled] of Object.entries(now)) {
        if (filled && !before?.[panel] && !expanded.value.includes(panel)) {
          expanded.value = [...expanded.value, panel]
        }
      }
    },
    { immediate: true }
  )
}
