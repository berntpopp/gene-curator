import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Router } from 'vue-router'
import { myWorkApi } from '@/api/myWork'
import { usePrecurationsStore } from '@/stores/precurations'

const POLL_MS = 60_000

/**
 * Navigation badges (My work, Review) from a single GET /me/work request.
 * Polling is owned here and ref-counted: any number of consumers (rail, tabs, palette)
 * call acquire()/release(), and the app still sends one request per interval.
 */
export const useWorkCountsStore = defineStore('workCounts', () => {
  const needsYou = ref(0)
  const review = ref(0)
  let holders = 0
  let teardown: (() => void) | null = null

  async function fetch() {
    try {
      const { items, counts } = await myWorkApi.getMyWork()
      // A late response must not restore a signed-out user's counts
      if (!holders) return
      needsYou.value = counts.needs_you ?? 0
      review.value = items.filter(i => i.kind === 'review' && i.tab === 'needs_you').length
    } catch {
      // Badge refresh must not break navigation; keep the last counts
    }
  }

  function reset() {
    needsYou.value = 0
    review.value = 0
  }

  function startPolling(router: Router) {
    void fetch()
    // Hidden tabs do not poll; coming back refreshes at once
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') void fetch()
    }
    const timer = setInterval(refreshWhenVisible, POLL_MS)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    // The count changes when a review item moves: after navigating and after
    // precuration approve/reject (which stay on the page).
    const stopAfterEach = router.afterEach(() => void fetch())
    const stopActions = usePrecurationsStore().$onAction(({ name, after }) => {
      if (/^(approve|reject)/.test(name)) after(() => void fetch())
    })
    teardown = () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
      stopAfterEach()
      stopActions()
      reset()
    }
  }

  /** Start polling if nobody else has; the router is used by the first holder only. */
  function acquire(router: Router) {
    if (holders++ === 0) startPolling(router)
  }

  function release() {
    if (holders > 0 && --holders === 0) {
      teardown?.()
      teardown = null
    }
  }

  return { needsYou, review, fetch, reset, acquire, release }
})
