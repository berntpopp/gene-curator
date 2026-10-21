import apiClient from '@/api/client'
import type { Schema } from '@/types/api'

export const myWorkApi = {
  /** The current user's work grouped by next action (backend/app/api/v1/endpoints/my_work.py). */
  async getMyWork(): Promise<Schema<'MyWorkResponse'>> {
    const response = await apiClient.get<Schema<'MyWorkResponse'>>('/me/work')
    return response.data
  }
}
