import { watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useWorkCountsStore } from '@/stores/workCounts'

/** My work and Review badge counts. Polling is shared in the store; this holds it while signed in. */
export function useWorkBadges() {
  const router = useRouter()
  const { isAuthenticated } = storeToRefs(useAuthStore())
  const counts = useWorkCountsStore()
  let held = false

  const sync = (signedIn: boolean) => {
    if (signedIn && !held) counts.acquire(router)
    else if (!signedIn && held) counts.release()
    held = signedIn
  }
  watch(isAuthenticated, sync, { immediate: true })
  onUnmounted(() => sync(false))

  return counts
}
