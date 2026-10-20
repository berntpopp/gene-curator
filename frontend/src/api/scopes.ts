import apiClient from './client'
import type { Schema } from '@/types/api'

export const scopesAPI = {
  /**
   * Get all scopes
   */
  async getScopes(params: Record<string, unknown> = {}): Promise<Schema<'ScopeListItem'>[]> {
    const response = await apiClient.get<Schema<'ScopeListItem'>[]>('/scopes', { params })
    return response.data
  },

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
    const response = await apiClient.post<Schema<'Scope'>>('/scopes', scopeData)
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
  async deleteScope(id: string, { force = false }: { force?: boolean } = {}): Promise<unknown> {
    const params = force ? { force: true } : {}
    const response = await apiClient.delete<unknown>(`/scopes/${id}`, { params })
    return response.data
  },

  /**
   * Get scope statistics
   */
  async getScopeStatistics(id: string): Promise<Schema<'ScopeStatistics'>> {
    const response = await apiClient.get<Schema<'ScopeStatistics'>>(`/scopes/${id}/statistics`)
    return response.data
  },

  /**
   * Get users in scope
   */
  async getScopeUsers(id: string): Promise<unknown> {
    const response = await apiClient.get<unknown>(`/scopes/${id}/users`)
    return response.data
  },

  /**
   * Assign user to scope
   */
  async assignUserToScope(
    scopeId: string,
    userId: string,
    roleData: Record<string, unknown>
  ): Promise<unknown> {
    const response = await apiClient.post<unknown>(`/scopes/${scopeId}/users/${userId}`, roleData)
    return response.data
  },

  /**
   * Remove user from scope
   */
  async removeUserFromScope(scopeId: string, userId: string): Promise<unknown> {
    const response = await apiClient.delete<unknown>(`/scopes/${scopeId}/users/${userId}`)
    return response.data
  }
}
