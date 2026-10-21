import { defineStore } from 'pinia'
import { ref } from 'vue'
import { myWorkApi } from '@/api/myWork'
import { logService } from '@/services/logService'
import { errorMessage } from './apiError'
import type { Schema } from '@/types/api'

export type WorkItem = Schema<'WorkItem'>
export type WorkTab = WorkItem['tab']

export const useMyWorkStore = defineStore('myWork', () => {
  const items = ref<WorkItem[]>([])
  const counts = ref<Record<string, number>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  const byTab = (tab: WorkTab) => items.value.filter(i => i.tab === tab)

  async function fetchMyWork() {
    loading.value = true
    error.value = null
    try {
      const data = await myWorkApi.getMyWork()
      items.value = data.items
      counts.value = data.counts
    } catch (err) {
      error.value = errorMessage(err, 'Failed to load your work')
      logService.error('Failed to load my work', { error: error.value })
    } finally {
      loading.value = false
    }
  }

  return { items, counts, loading, error, byTab, fetchMyWork }
})
