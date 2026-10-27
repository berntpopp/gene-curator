import apiClient from './client'
import type { Schema } from '@/types/api'

const ADMIN = '/admin/llm'

/** LLM configuration (#489). Admin endpoints are platform admin only; keys are write-only. */
export const llmAPI = {
  async listProviders(): Promise<Schema<'ProviderOut'>[]> {
    return (await apiClient.get<Schema<'ProviderOut'>[]>(`${ADMIN}/providers`)).data
  },
  async createProvider(data: Schema<'ProviderCreate'>): Promise<Schema<'ProviderOut'>> {
    return (await apiClient.post<Schema<'ProviderOut'>>(`${ADMIN}/providers`, data)).data
  },
  async updateProvider(id: string, data: Schema<'ProviderUpdate'>): Promise<Schema<'ProviderOut'>> {
    return (await apiClient.patch<Schema<'ProviderOut'>>(`${ADMIN}/providers/${id}`, data)).data
  },
  /** Write-only: the response is 204 and nothing ever reads the key back. */
  async setKey(id: string, data: Schema<'ProviderKey'>): Promise<void> {
    await apiClient.put(`${ADMIN}/providers/${id}/key`, data)
  },
  async ping(id: string, data: Schema<'PingRequest'> = {}): Promise<Schema<'PingOut'>> {
    return (await apiClient.post<Schema<'PingOut'>>(`${ADMIN}/providers/${id}/ping`, data)).data
  },

  async listModels(): Promise<Schema<'ModelOut'>[]> {
    return (await apiClient.get<Schema<'ModelOut'>[]>(`${ADMIN}/models`)).data
  },
  async createModel(data: Schema<'ModelCreate'>): Promise<Schema<'ModelOut'>> {
    return (await apiClient.post<Schema<'ModelOut'>>(`${ADMIN}/models`, data)).data
  },
  async updateModel(id: string, data: Schema<'ModelUpdate'>): Promise<Schema<'ModelOut'>> {
    return (await apiClient.patch<Schema<'ModelOut'>>(`${ADMIN}/models/${id}`, data)).data
  },

  async usage(): Promise<Schema<'UsageRow'>[]> {
    return (await apiClient.get<Schema<'UsageRow'>[]>(`${ADMIN}/usage`)).data
  },
  async listRuns(params: { scope_id?: string; limit?: number } = {}): Promise<Schema<'RunOut'>[]> {
    return (await apiClient.get<Schema<'RunOut'>[]>(`${ADMIN}/runs`, { params })).data
  },

  async listTemplates(): Promise<Schema<'TemplateOut'>[]> {
    return (await apiClient.get<Schema<'TemplateOut'>[]>(`${ADMIN}/prompt-templates`)).data
  },
  async createTemplate(data: Schema<'TemplateCreate'>): Promise<Schema<'TemplateOut'>> {
    return (await apiClient.post<Schema<'TemplateOut'>>(`${ADMIN}/prompt-templates`, data)).data
  },
  async listVersions(templateId: string): Promise<Schema<'VersionOut'>[]> {
    const url = `${ADMIN}/prompt-templates/${templateId}/versions`
    return (await apiClient.get<Schema<'VersionOut'>[]>(url)).data
  },
  async createVersion(
    templateId: string,
    data: Schema<'VersionCreate'>
  ): Promise<Schema<'VersionOut'>> {
    const url = `${ADMIN}/prompt-templates/${templateId}/versions`
    return (await apiClient.post<Schema<'VersionOut'>>(url, data)).data
  },
  /** On a published version the server creates a new draft instead. */
  async updateVersion(id: string, data: Schema<'VersionUpdate'>): Promise<Schema<'VersionOut'>> {
    return (await apiClient.patch<Schema<'VersionOut'>>(`${ADMIN}/prompt-versions/${id}`, data))
      .data
  },
  async publishVersion(id: string, data: Schema<'Revision'>): Promise<Schema<'VersionOut'>> {
    const url = `${ADMIN}/prompt-versions/${id}/publish`
    return (await apiClient.post<Schema<'VersionOut'>>(url, data)).data
  },
  /** Unified diff from `against` (old) to `id` (new). */
  async diffVersions(id: string, against: string): Promise<Schema<'VersionDiff'>> {
    const url = `${ADMIN}/prompt-versions/${id}/diff`
    return (await apiClient.get<Schema<'VersionDiff'>>(url, { params: { against } })).data
  },

  /** Runs the version over the server's golden set with one model; nothing is stored. */
  async testRun(id: string, data: Schema<'TestRunRequest'>): Promise<Schema<'TestRunOut'>> {
    const url = `${ADMIN}/prompt-versions/${id}/test-run`
    return (await apiClient.post<Schema<'TestRunOut'>>(url, data)).data
  },

  async scopeOptions(scopeId: string): Promise<Schema<'ScopeLLMOptions'>> {
    return (await apiClient.get<Schema<'ScopeLLMOptions'>>(`/scopes/${scopeId}/llm-options`)).data
  },
  async scopeSettings(scopeId: string): Promise<Schema<'ScopeSettingsOut'>> {
    return (await apiClient.get<Schema<'ScopeSettingsOut'>>(`/scopes/${scopeId}/llm-settings`)).data
  },
  async saveScopeSettings(
    scopeId: string,
    data: Schema<'ScopeSettingsUpdate'>
  ): Promise<Schema<'ScopeSettingsOut'>> {
    const url = `/scopes/${scopeId}/llm-settings`
    return (await apiClient.put<Schema<'ScopeSettingsOut'>>(url, data)).data
  }
}
