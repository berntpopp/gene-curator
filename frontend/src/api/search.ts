import apiClient from './client'
import type { Schema } from '@/types/api'

export const searchAPI = {
  /** Grouped genes, curations and scopes for the command palette (q is 2 to 100 characters). */
  async search(q: string, signal?: AbortSignal): Promise<Schema<'SearchResponse'>> {
    const response = await apiClient.get<Schema<'SearchResponse'>>('/search', {
      params: { q },
      signal
    })
    return response.data
  }
}
