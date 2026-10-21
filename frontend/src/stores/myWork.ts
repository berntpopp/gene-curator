import { defineStore } from 'pinia'
import { ref } from 'vue'
import { myWorkApi } from '@/api/myWork'
import { logService } from '@/services/logService'
import { errorMessage } from './apiError'
import { useAuthStore } from './auth'
import { useReviewFeedbackStore } from './reviewFeedback'
import { useScopesStore } from './scopes'
import type { Schema } from '@/types/api'

export type WorkItem = Schema<'WorkItem'>
export type WorkTab = WorkItem['tab']

export const useMyWorkStore = defineStore('myWork', () => {
  const items = ref<WorkItem[]>([])
  const counts = ref<Record<string, number>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  const byTab = (tab: WorkTab) => items.value.filter(i => i.tab === tab)

  /** Display names instead of slugs; unknown scopes keep the API name. */
  async function scopeNames(): Promise<Map<string, string>> {
    const scopes = useScopesStore()
    try {
      if (!scopes.scopes.length) await scopes.fetchUserScopes()
    } catch {
      // keep the API names
    }
    return new Map(scopes.scopes.map(s => [s.id, s.display_name || s.name]))
  }

  /** The review actions of a precuration live in the review queue, so My work links there. */
  async function decorate(list: WorkItem[]): Promise<WorkItem[]> {
    const names = await scopeNames()
    return list.map(i => {
      const row = { ...i, scope_name: names.get(i.scope_id) ?? i.scope_name }
      if (i.kind === 'review' && i.item_type === 'precuration') {
        row.link = `/review-queue?q=${encodeURIComponent(i.gene_symbol)}`
      }
      return row
    })
  }

  let generation = 0
  const LOOKUPS = 4

  /**
   * A draft curation that a reviewer sent back reads "Address review feedback". Looked up after the
   * list is shown, four at a time; labels for a list that was since replaced are dropped.
   * ponytail: /me/work should return a feedback flag so this needs no requests per draft (backend).
   */
  async function labelFeedback(gen: number) {
    const me = (useAuthStore().user as { id?: string } | null)?.id ?? ''
    const feedback = useReviewFeedbackStore()
    const drafts = items.value.filter(i => i.kind === 'draft' && i.item_type === 'curation')
    let next = 0
    const worker = async () => {
      while (next < drafts.length) {
        const row = drafts[next++]!
        const fb = await feedback.fetch(row.item_id, me).catch(() => null)
        if (fb?.any && gen === generation) {
          items.value = items.value.map(i =>
            i.item_id === row.item_id && i.kind === row.kind
              ? { ...i, verb: 'Address review feedback' }
              : i
          )
        }
      }
    }
    await Promise.all(Array.from({ length: Math.min(LOOKUPS, drafts.length) }, worker))
  }

  async function fetchMyWork() {
    loading.value = true
    error.value = null
    try {
      const data = await myWorkApi.getMyWork()
      items.value = await decorate(data.items)
      void labelFeedback(++generation)
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
