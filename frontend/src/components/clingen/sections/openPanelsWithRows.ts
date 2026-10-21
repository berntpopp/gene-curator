import { watch, type Ref } from 'vue'
import { rows } from '@/components/curation/evidenceCounts'

/** Open each panel the moment it gains rows (mount, restore); never re-open one the user closed. */
export function openPanelsWithRows(
  expanded: Ref<string[]>,
  groups: () => Record<string, unknown>
): void {
  watch(
    () => Object.fromEntries(Object.entries(groups()).map(([k, v]) => [k, rows(v).length > 0])),
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
