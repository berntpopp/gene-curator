import apiClient from './client'
import type { Schema } from '@/types/api'

export const scopesAPI = {
  /**
   * Get scope by ID
   */
  async getScopeById(id: string): Promise<Schema<'ScopeWithStats'>> {
    const response = await apiClient.get<Schema<'ScopeWithStats'>>(`/scopes/${id}`)
    return response.data
  },

  /**
   * Create new scope
   */
  async createScope(scopeData: Schema<'ScopeCreate'>): Promise<Schema<'Scope'>> {
    const response = await apiClient.post<Schema<'Scope'>>('/scopes/', scopeData)
    return response.data
  },

  /**
   * Update scope (partial update)
   */
  async updateScope(id: string, scopeData: Schema<'ScopeUpdate'>): Promise<Schema<'Scope'>> {
    const response = await apiClient.patch<Schema<'Scope'>>(`/scopes/${id}`, scopeData)
    return response.data
  },

  /**
   * Delete scope
   * @param id - Scope ID
   * @param options - Options
   * @param options.force - Force deletion even with active gene assignments
   */
  async deleteScope(id: string, { force = false }: { force?: boolean } = {}): Promise<void> {
    const params = force ? { force: true } : {}
    await apiClient.delete(`/scopes/${id}`, { params })
  },

  /**
   * Get scope statistics
   */
  async getScopeStatistics(id: string): Promise<Schema<'ScopeStatistics'>> {
    const response = await apiClient.get<Schema<'ScopeStatistics'>>(`/scopes/${id}/statistics`)
    return response.data
  }
}
