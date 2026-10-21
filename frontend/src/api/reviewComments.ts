import apiClient from './client'
import type { Schema } from '@/types/api'

export const reviewCommentsAPI = {
  /** Evidence changes since the version the reviewer last saw (all items added on a first review). */
  async getDiff(curationId: string): Promise<Schema<'CurationDiff'>> {
    const r = await apiClient.get<Schema<'CurationDiff'>>(`/curations/${curationId}/diff`)
    return r.data
  },

  async list(curationId: string): Promise<Schema<'ReviewComment'>[]> {
    const r = await apiClient.get<Schema<'ReviewComment'>[]>(
      `/curations/${curationId}/review-comments`
    )
    return r.data
  },

  async create(
    curationId: string,
    body: Schema<'ReviewCommentCreate'>
  ): Promise<Schema<'ReviewComment'>> {
    const r = await apiClient.post<Schema<'ReviewComment'>>(
      `/curations/${curationId}/review-comments`,
      body
    )
    return r.data
  },

  async update(
    curationId: string,
    commentId: string,
    body: Schema<'ReviewCommentUpdate'>
  ): Promise<Schema<'ReviewComment'>> {
    const r = await apiClient.patch<Schema<'ReviewComment'>>(
      `/curations/${curationId}/review-comments/${commentId}`,
      body
    )
    return r.data
  },

  /** Item ids (curations and precurations) with a review still pending for me. */
  async myPendingItemIds(): Promise<string[]> {
    const r = await apiClient.get<Schema<'PeerReviewRequest'>[]>(
      '/workflow/reviews/my-assignments',
      {
        params: { status: 'pending', limit: 200 }
      }
    )
    return r.data.map(a => a.item_id)
  }
}
