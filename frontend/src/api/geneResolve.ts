import apiClient from './client'
import type { Schema } from '@/types/api'

export const geneResolveAPI = {
  /**
   * Resolve pasted symbols, previous symbols, aliases and HGNC IDs (input order is kept);
   * with a scope, candidates already in it carry `in_scope` and `in_scope_curator`.
   */
  async resolve(symbols: string[], scopeId?: string): Promise<Schema<'GeneResolveResponse'>> {
    const response = await apiClient.post<Schema<'GeneResolveResponse'>>('/genes/resolve', {
      symbols,
      ...(scopeId ? { scope_id: scopeId } : {})
    })
    return response.data
  }
}
