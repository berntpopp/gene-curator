/** Catalogue genes x scopes matrix (read-only). */
import apiClient from './client'
import type { Schema } from '@/types/api'

export interface MatrixQuery {
  scope_ids: string[]
  search?: string
  agreement?: 'agree' | 'disagree'
  skip?: number
  limit?: number
  sort_order?: 'asc' | 'desc'
}

export const catalogueMatrixAPI = {
  async getMatrix(params: MatrixQuery): Promise<Schema<'MatrixResponse'>> {
    const response = await apiClient.get<Schema<'MatrixResponse'>>('/gene-catalogue/matrix', {
      params,
      // scope_ids=a&scope_ids=b, not scope_ids[]=a (the endpoint expects repeated keys)
      paramsSerializer: { indexes: null }
    })
    return response.data
  },

  async getScopes(): Promise<Schema<'ScopeFilterOption'>[]> {
    const response = await apiClient.get<Schema<'ScopeFilterOption'>[]>(
      '/gene-catalogue/filters/scopes'
    )
    return response.data
  }
}
