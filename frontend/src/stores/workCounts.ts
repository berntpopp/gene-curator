import { defineStore } from 'pinia'
import { ref } from 'vue'
import { myWorkAPI } from '@/api/myWork'

/** Navigation badges (My work, Review) from a single GET /me/work request. */
export const useWorkCountsStore = defineStore('workCounts', () => {
  const needsYou = ref(0)
  const review = ref(0)

  async function fetch() {
    try {
      const { items, counts } = await myWorkAPI.get()
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

  return { needsYou, review, fetch, reset }
})
