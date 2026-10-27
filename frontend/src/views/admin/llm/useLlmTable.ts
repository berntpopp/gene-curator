import { computed, type Ref } from 'vue'
import { clientPage } from '@/components/common/tableRows'
import { useTableUrlState } from '@/composables/useTableUrlState'

/** URL-backed state for one client-side DataTable on the LLM console; search matches any cell. */
export function useLlmTable<T extends object>(prefix: string, rows: Ref<T[]>) {
  const state = useTableUrlState({ prefix, pageSize: 10 })
  const matching = computed(() => {
    const q = state.search.value.trim().toLowerCase()
    return q
      ? rows.value.filter(r => Object.values(r).some(v => String(v).toLowerCase().includes(q)))
      : rows.value
  })
  const shown = computed(() =>
    clientPage(matching.value, {
      sortBy: state.sortBy.value,
      page: state.page.value,
      itemsPerPage: state.itemsPerPage.value
    })
  )
  return { ...state, shown, total: computed(() => matching.value.length) }
}
