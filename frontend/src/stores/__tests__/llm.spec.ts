import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { llmAPI } from '@/api/llm'
import { llmErrorMessage, useLlmStore } from '@/stores/llm'
import type { Schema } from '@/types/api'

vi.mock('@/api/llm', () => ({
  llmAPI: {
    listProviders: vi.fn(),
    createProvider: vi.fn(),
    updateProvider: vi.fn(),
    setKey: vi.fn(),
    ping: vi.fn(),
    listModels: vi.fn(),
    createModel: vi.fn(),
    updateModel: vi.fn(),
    usage: vi.fn(),
    listRuns: vi.fn(),
    listTemplates: vi.fn(),
    createTemplate: vi.fn(),
    listVersions: vi.fn(),
    createVersion: vi.fn(),
    updateVersion: vi.fn(),
    publishVersion: vi.fn(),
    diffVersions: vi.fn(),
    scopeOptions: vi.fn(),
    scopeSettings: vi.fn(),
    saveScopeSettings: vi.fn()
  }
}))

const api = vi.mocked(llmAPI)
const SECRET = 'sk-live-very-secret-key-value'
const httpError = (status: number, detail: string) => ({ response: { status, data: { detail } } })

const provider = (over: Partial<Schema<'ProviderOut'>> = {}): Schema<'ProviderOut'> => ({
  id: 'p1',
  name: 'Anthropic',
  kind: 'anthropic',
  base_url: 'https://api.anthropic.com',
  enabled: true,
  lock_version: 1,
  has_key: false,
  key_fingerprint: null,
  created_at: '2026-10-01T00:00:00Z',
  ...over
})

const version = (over: Partial<Schema<'VersionOut'>> = {}): Schema<'VersionOut'> => ({
  id: 'v1',
  template_id: 't1',
  version: 1,
  system_text: 's',
  user_text: 'u',
  output_schema: {},
  few_shot_examples: [],
  sha256: null,
  published_at: null,
  derived_from: null,
  lock_version: 0,
  created_at: '2026-10-01T00:00:00Z',
  ...over
})

describe('llmErrorMessage', () => {
  it('names stale saves and fail-closed outages, passes other errors through', () => {
    expect(llmErrorMessage(httpError(409, 'Changed by someone else'), 'x')).toBe(
      'Not saved, conflict: Changed by someone else'
    )
    expect(llmErrorMessage(httpError(503, 'Audit log unavailable'), 'x')).toBe(
      'Not saved, service unavailable: Audit log unavailable'
    )
    expect(llmErrorMessage(httpError(422, 'Bad URL'), 'x')).toBe('Bad URL')
    expect(llmErrorMessage(null, 'fallback')).toBe('fallback')
  })
})

describe('llm store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads providers, models and templates, and reports a failed load', async () => {
    api.listProviders.mockResolvedValue([provider()])
    api.listModels.mockResolvedValue([])
    api.listTemplates.mockResolvedValue([])
    const store = useLlmStore()
    await store.fetchConfig()
    expect(store.providers).toHaveLength(1)
    expect(store.error).toBeNull()

    api.listProviders.mockRejectedValue(httpError(503, 'Audit log unavailable'))
    await store.fetchConfig()
    expect(store.error).toContain('service unavailable')
    expect(store.loading).toBe(false)
  })

  it('sends the key to the API and keeps only the refreshed fingerprint (#489)', async () => {
    api.setKey.mockResolvedValue(undefined)
    api.listProviders.mockResolvedValue([provider({ has_key: true, key_fingerprint: 'ab12' })])
    const store = useLlmStore()
    await store.setKey('p1', SECRET)

    expect(api.setKey).toHaveBeenCalledWith('p1', { api_key: SECRET })
    expect(store.providers[0]!.key_fingerprint).toBe('ab12')
    expect(JSON.stringify(store.$state)).not.toContain(SECRET)
  })

  it('creates and updates providers and models in place', async () => {
    const store = useLlmStore()
    api.createProvider.mockResolvedValue(provider())
    await store.saveProvider(null, {
      name: 'A',
      kind: 'anthropic',
      base_url: 'https://x',
      enabled: true
    })
    api.updateProvider.mockResolvedValue(provider({ name: 'Renamed', lock_version: 2 }))
    await store.saveProvider('p1', { name: 'Renamed', lock_version: 1 })
    expect(store.providers).toEqual([provider({ name: 'Renamed', lock_version: 2 })])

    const model = {
      id: 'm1',
      provider_id: 'p1',
      model_id: 'claude-x-20250929',
      input_price_per_mtok_cents: '300',
      output_price_per_mtok_cents: '1500',
      max_tokens: 4096,
      timeout_s: 60,
      uses_max_completion_tokens: false,
      enabled: true,
      lock_version: 0
    }
    api.createModel.mockResolvedValue(model)
    await store.saveModel(null, { ...model, id: undefined } as never)
    api.updateModel.mockResolvedValue({ ...model, enabled: false, lock_version: 1 })
    await store.saveModel('m1', { enabled: false, lock_version: 0 })
    expect(store.models).toHaveLength(1)
    expect(store.models[0]!.enabled).toBe(false)
  })

  it('creates templates, saves and publishes versions, loads activity', async () => {
    const store = useLlmStore()
    const template = {
      id: 't1',
      key: 'k',
      strategy: 'skeptic' as const,
      description: null,
      created_at: '2026-10-01T00:00:00Z'
    }
    api.createTemplate.mockResolvedValue(template)
    expect(await store.createTemplate({ key: 'k', strategy: 'skeptic' })).toEqual(template)
    expect(store.templates).toEqual([template])

    api.createVersion.mockResolvedValue(version())
    api.listVersions.mockResolvedValue([version()])
    await store.saveVersion('t1', null, { system_text: 's', user_text: 'u' })
    expect(api.createVersion).toHaveBeenCalledWith('t1', { system_text: 's', user_text: 'u' })

    api.updateVersion.mockResolvedValue(version({ id: 'v2', version: 2 }))
    await store.saveVersion('t1', 'v1', { system_text: 's2', user_text: 'u', lock_version: 3 })
    expect(api.updateVersion).toHaveBeenCalledWith('v1', {
      system_text: 's2',
      user_text: 'u',
      lock_version: 3
    })
    await store.saveVersion('t1', 'v1', { system_text: 's2', user_text: 'u' })
    expect(api.updateVersion).toHaveBeenLastCalledWith(
      'v1',
      expect.objectContaining({ lock_version: 0 })
    )

    api.publishVersion.mockResolvedValue(version({ published_at: '2026-10-02T00:00:00Z' }))
    await store.publishVersion(version())
    expect(api.publishVersion).toHaveBeenCalledWith('v1', { lock_version: 0 })
    expect(store.versions[0]!.published_at).not.toBeNull()

    api.listVersions.mockResolvedValue([])
    await store.fetchVersions('t1')
    expect(store.versions).toEqual([])

    api.usage.mockResolvedValue([])
    api.listRuns.mockResolvedValue([])
    await store.fetchActivity()
    expect(api.listRuns).toHaveBeenCalledWith({ limit: 500 })

    api.ping.mockResolvedValue({ ok: true, model: 'm', latency_ms: 5 })
    expect((await store.ping('p1')).ok).toBe(true)
    api.diffVersions.mockResolvedValue({} as never)
    await store.diffVersions('v2', 'v1')
    expect(api.diffVersions).toHaveBeenCalledWith('v2', 'v1')
  })
})
