import apiClient from './client'
import type { Schema } from '@/types/api'

export const geneResolveAPI = {
  /** Resolve pasted symbols, previous symbols, aliases and HGNC IDs (input order is kept). */
  async resolve(symbols: string[]): Promise<Schema<'GeneResolveResponse'>> {
    const response = await apiClient.post<Schema<'GeneResolveResponse'>>('/genes/resolve', {
      symbols
    })
    return response.data
  }
}
