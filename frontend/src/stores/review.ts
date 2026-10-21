import { defineStore } from 'pinia'
import { ref } from 'vue'
import { reviewCommentsAPI } from '@/api/reviewComments'
import { errorMessage } from './apiError'
import type { Schema } from '@/types/api'

type Comment = Schema<'ReviewComment'>

/** Diff and per-item comments of the curation under review. Accepting is an open `accepted` row; withdrawing resolves it. */
export const useReviewStore = defineStore('review', () => {
  const curationId = ref('')
  const diff = ref<Schema<'CurationDiff'> | null>(null)
  const comments = ref<Comment[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(id: string) {
    curationId.value = id
    loading.value = true
    error.value = null
    try {
      ;[diff.value, comments.value] = await Promise.all([
        reviewCommentsAPI.getDiff(id),
        reviewCommentsAPI.list(id)
      ])
    } catch (e) {
      error.value = errorMessage(e, 'Could not load the review')
    } finally {
      loading.value = false
    }
  }

  const replace = (c: Comment) => {
    const i = comments.value.findIndex(x => x.id === c.id)
    if (i === -1) comments.value.push(c)
    else comments.value[i] = c
  }

  async function accept(itemPath: string) {
    replace(
      await reviewCommentsAPI.create(curationId.value, { item_path: itemPath, kind: 'accepted' })
    )
  }

  /** A new query on an item, or a reply in its thread. */
  async function query(itemPath: string, body: string) {
    replace(
      await reviewCommentsAPI.create(curationId.value, { item_path: itemPath, kind: 'query', body })
    )
  }

  async function setStatus(id: string, status: 'open' | 'resolved') {
    replace(await reviewCommentsAPI.update(curationId.value, id, { status }))
  }

  const withdraw = (id: string) => setStatus(id, 'resolved')

  async function resolveThread(itemPath: string) {
    const open = comments.value.filter(
      c => c.item_path === itemPath && c.kind === 'query' && c.status === 'open'
    )
    for (const c of open) await setStatus(c.id, 'resolved')
  }

  /** Ids of curations and precurations I was assigned to review and have not decided. */
  async function fetchMyPending(): Promise<Set<string>> {
    return new Set(await reviewCommentsAPI.myPendingItemIds())
  }

  return {
    curationId,
    diff,
    comments,
    loading,
    error,
    load,
    accept,
    query,
    withdraw,
    resolveThread,
    fetchMyPending
  }
})
