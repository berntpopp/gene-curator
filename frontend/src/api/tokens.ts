import apiClient from './client'
import type { Schema } from '@/types/api'

export const tokensAPI = {
  /** List the current user's personal access tokens (never their plaintext) */
  async list(): Promise<Schema<'PersonalAccessTokenResponse'>[]> {
    const response = await apiClient.get<Schema<'PersonalAccessTokenResponse'>[]>('/me/tokens/')
    return response.data
  },

  /** Create a token; the response holds the plaintext exactly once */
  async create(
    data: Schema<'PersonalAccessTokenCreate'>
  ): Promise<Schema<'PersonalAccessTokenCreated'>> {
    const response = await apiClient.post<Schema<'PersonalAccessTokenCreated'>>('/me/tokens/', data)
    return response.data
  },

  /** Revoke one of the current user's tokens */
  async revoke(id: string): Promise<void> {
    await apiClient.delete(`/me/tokens/${id}`)
  }
}
