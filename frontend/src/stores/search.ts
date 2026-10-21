import { defineStore } from 'pinia'
import { ref } from 'vue'
import { searchAPI } from '@/api/search'
import type { Schema } from '@/types/api'

export const SEARCH_DEBOUNCE_MS = 200
export const SEARCH_MIN_CHARS = 2 // the backend answers 422 below this

/** Command palette state: open/closed, the query and its debounced, cancellable lookup. */
export const useSearchStore = defineStore('search', () => {
  const isOpen = ref(false)
  const showHelp = ref(false)
  const query = ref('')
  const results = ref<Schema<'SearchResponse'> | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  let timer: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | undefined

  function cancel() {
    clearTimeout(timer)
    controller?.abort()
    controller = undefined
    loading.value = false
  }

  async function run(q: string) {
    const mine = (controller = new AbortController())
    try {
      const data = await searchAPI.search(q, mine.signal)
      if (controller === mine) results.value = data
    } catch {
      if (controller === mine) {
        results.value = null
        error.value = 'Search failed. Try again.'
      }
    } finally {
      if (controller === mine) loading.value = false
    }
  }

  function setQuery(value: string) {
    query.value = value
    cancel()
    error.value = null
    const q = value.trim()
    if (q.length < SEARCH_MIN_CHARS) {
      results.value = null
      return
    }
    loading.value = true
    timer = setTimeout(() => void run(q), SEARCH_DEBOUNCE_MS)
  }

  function open(opts: { help?: boolean } = {}) {
    showHelp.value = !!opts.help
    isOpen.value = true
  }

  function close() {
    cancel()
    isOpen.value = false
    showHelp.value = false
    query.value = ''
    results.value = null
    error.value = null
  }

  return { isOpen, showHelp, query, results, loading, error, setQuery, open, close }
})
