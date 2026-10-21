import { watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useWorkCountsStore } from '@/stores/workCounts'
import { usePrecurationsStore } from '@/stores/precurations'

/** My work and Review badge counts (one /me/work request); polls while signed in. Mount in one nav at a time. */
export function useWorkBadges() {
  const router = useRouter()
  const { isAuthenticated } = storeToRefs(useAuthStore())
  const counts = useWorkCountsStore()
  let badgeRefreshInterval: ReturnType<typeof setInterval> | null = null

  const refreshBadgeCount = () => counts.fetch()

  // Hidden tabs do not poll; coming back refreshes at once
  function refreshWhenVisible() {
    if (document.visibilityState === 'visible') refreshBadgeCount()
  }

  function startBadgeRefresh() {
    if (!badgeRefreshInterval) {
      refreshBadgeCount()
      badgeRefreshInterval = setInterval(refreshWhenVisible, 60000)
      document.addEventListener('visibilitychange', refreshWhenVisible)
    }
  }

  function stopBadgeRefresh() {
    if (badgeRefreshInterval) {
      clearInterval(badgeRefreshInterval)
      badgeRefreshInterval = null
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
    counts.reset()
  }

  onMounted(() => {
    if (isAuthenticated.value) {
      startBadgeRefresh()
    }
  })

  watch(isAuthenticated, newVal => {
    if (newVal) {
      startBadgeRefresh()
    } else {
      stopBadgeRefresh()
    }
  })

  // The queue count changes when a review item moves: after navigating (curation review
  // returns to the queue) and after precuration approve/reject (which stay on the page).
  const stopAfterEach = router.afterEach(() => {
    if (isAuthenticated.value) refreshBadgeCount()
  })
  const stopActions = usePrecurationsStore().$onAction(({ name, after }) => {
    if (/^(approve|reject)/.test(name)) after(() => refreshBadgeCount())
  })

  onUnmounted(() => {
    stopAfterEach()
    stopActions()
    stopBadgeRefresh()
  })

  return counts
}
