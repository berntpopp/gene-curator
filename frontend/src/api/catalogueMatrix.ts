/** Catalogue genes x scopes matrix (read-only). */
import apiClient from './client'
import type { Schema } from '@/types/api'

export interface MatrixQuery {
  scope_ids: string[]
  search?: string
  agreement?: 'agree' | 'disagree'
  classification?: string
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

  /** Classes with an active curation the caller may see (lower case). */
  async getClassifications(): Promise<string[]> {
    const response = await apiClient.get<string[]>('/gene-catalogue/filters/classifications')
    return response.data
  },

  /** The signed-in user's saved columns, in order; empty when none were chosen (#276). */
  async getSavedView(): Promise<string[]> {
    const response = await apiClient.get<Schema<'CatalogueView'>>('/me/views/catalogue')
    return response.data.scope_ids ?? []
  },

  async saveView(scopeIds: string[]): Promise<void> {
    await apiClient.put('/me/views/catalogue', { scope_ids: scopeIds })
  },

  async getScopes(): Promise<Schema<'ScopeFilterOption'>[]> {
    const response = await apiClient.get<Schema<'ScopeFilterOption'>[]>(
      '/gene-catalogue/filters/scopes'
    )
    return response.data
  }
}
