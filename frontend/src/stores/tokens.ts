/**
 * Personal access tokens store (#462): list, create and revoke the user's own tokens.
 * The plaintext of a new token is returned to the caller once and never kept in state.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tokensAPI } from '@/api/tokens'
import { errorMessage } from './apiError'
import type { Schema } from '@/types/api'

export type PersonalAccessToken = Schema<'PersonalAccessTokenResponse'>

export const useTokensStore = defineStore('tokens', () => {
  const tokens = ref<PersonalAccessToken[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchTokens = async (): Promise<void> => {
    loading.value = true
    error.value = null
    try {
      tokens.value = await tokensAPI.list()
    } catch (err) {
      error.value = errorMessage(err, 'Failed to load tokens')
    } finally {
      loading.value = false
    }
  }

  /** Returns the plaintext token; the caller shows it once. */
  const createToken = async (data: Schema<'PersonalAccessTokenCreate'>): Promise<string> => {
    const { token, ...listed } = await tokensAPI.create(data)
    tokens.value.unshift(listed)
    return token
  }

  const revokeToken = async (id: string): Promise<void> => {
    await tokensAPI.revoke(id)
    await fetchTokens()
  }

  return { tokens, loading, error, fetchTokens, createToken, revokeToken }
})
