/**
 * LLM configuration store (#489): providers, models, prompts, usage and runs for platform
 * admins, plus the scope opt-in panel. API keys pass through `setKey` and are never kept here.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { llmAPI } from '@/api/llm'
import { toApiError } from './apiError'
import { readableApiError } from '@/utils/apiErrorText'
import type { Schema } from '@/types/api'

export type LlmProvider = Schema<'ProviderOut'>
export type LlmModel = Schema<'ModelOut'>
export type PromptTemplate = Schema<'TemplateOut'>
export type PromptVersion = Schema<'VersionOut'>
export type LlmRun = Schema<'RunOut'>
export type UsageRow = Schema<'UsageRow'>

/** One sentence for a failed LLM admin call; stale saves (409) and fail-closed 503s say so. */
export function llmErrorMessage(error: unknown, fallback: string): string {
  const status = toApiError(error).response?.status
  const text = readableApiError(error, fallback)
  if (status === 409) return `Not saved, conflict: ${text}`
  if (status === 503) return `Not saved, service unavailable: ${text}`
  return text
}

export const useLlmStore = defineStore('llm', () => {
  const providers = ref<LlmProvider[]>([])
  const models = ref<LlmModel[]>([])
  const templates = ref<PromptTemplate[]>([])
  const versions = ref<PromptVersion[]>([])
  const usage = ref<UsageRow[]>([])
  const runs = ref<LlmRun[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(task: () => Promise<void>, fallback: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await task()
    } catch (err) {
      error.value = llmErrorMessage(err, fallback)
    } finally {
      loading.value = false
    }
  }

  const fetchConfig = () =>
    load(async () => {
      ;[providers.value, models.value, templates.value] = await Promise.all([
        llmAPI.listProviders(),
        llmAPI.listModels(),
        llmAPI.listTemplates()
      ])
    }, 'Failed to load LLM configuration')

  const fetchActivity = () =>
    load(async () => {
      ;[usage.value, runs.value] = await Promise.all([
        llmAPI.usage(),
        llmAPI.listRuns({ limit: 500 })
      ])
    }, 'Failed to load LLM usage')

  // The template whose versions are shown; a late response for another one is dropped
  let versionsOf: string | null = null
  async function loadVersions(templateId: string): Promise<void> {
    const rows = await llmAPI.listVersions(templateId)
    if (versionsOf === templateId) versions.value = rows
  }

  const fetchVersions = (templateId: string) => {
    versionsOf = templateId
    versions.value = []
    return load(() => loadVersions(templateId), 'Failed to load prompt versions')
  }

  const replace = <T extends { id: string }>(list: T[], row: T): T[] => {
    const i = list.findIndex(r => r.id === row.id)
    return i < 0 ? [...list, row] : list.map(r => (r.id === row.id ? row : r))
  }

  async function saveProvider(
    id: string | null,
    data: Schema<'ProviderCreate'> | Schema<'ProviderUpdate'>
  ): Promise<void> {
    const row = id
      ? await llmAPI.updateProvider(id, data as Schema<'ProviderUpdate'>)
      : await llmAPI.createProvider(data as Schema<'ProviderCreate'>)
    providers.value = replace(providers.value, row)
  }

  /** The key goes straight to the API; only the refreshed has_key and fingerprint come back. */
  async function setKey(providerId: string, apiKey: string): Promise<void> {
    await llmAPI.setKey(providerId, { api_key: apiKey })
    providers.value = await llmAPI.listProviders()
  }

  const ping = (providerId: string) => llmAPI.ping(providerId)

  async function saveModel(
    id: string | null,
    data: Schema<'ModelCreate'> | Schema<'ModelUpdate'>
  ): Promise<void> {
    const row = id
      ? await llmAPI.updateModel(id, data as Schema<'ModelUpdate'>)
      : await llmAPI.createModel(data as Schema<'ModelCreate'>)
    models.value = replace(models.value, row)
  }

  async function createTemplate(data: Schema<'TemplateCreate'>): Promise<PromptTemplate> {
    const row = await llmAPI.createTemplate(data)
    templates.value = replace(templates.value, row)
    return row
  }

  /** Saves a draft; editing a published version makes the server create a new draft. */
  async function saveVersion(
    templateId: string,
    id: string | null,
    data: Schema<'VersionCreate'> & { lock_version?: number }
  ): Promise<PromptVersion> {
    const row = id
      ? await llmAPI.updateVersion(id, { ...data, lock_version: data.lock_version ?? 0 })
      : await llmAPI.createVersion(templateId, data)
    await loadVersions(templateId)
    return row
  }

  async function publishVersion(version: PromptVersion): Promise<void> {
    const row = await llmAPI.publishVersion(version.id, { lock_version: version.lock_version })
    versions.value = replace(versions.value, row)
  }

  const diffVersions = (id: string, against: string) => llmAPI.diffVersions(id, against)

  return {
    providers,
    models,
    templates,
    versions,
    usage,
    runs,
    loading,
    error,
    fetchConfig,
    fetchActivity,
    fetchVersions,
    saveProvider,
    setKey,
    ping,
    saveModel,
    createTemplate,
    saveVersion,
    publishVersion,
    diffVersions,
    testRun: llmAPI.testRun,
    scopeOptions: llmAPI.scopeOptions,
    scopeSettings: llmAPI.scopeSettings,
    saveScopeSettings: llmAPI.saveScopeSettings,
    secondView: llmAPI.secondView,
    requestSecondView: llmAPI.requestSecondView,
    decideFinding: llmAPI.decideFinding
  }
})
