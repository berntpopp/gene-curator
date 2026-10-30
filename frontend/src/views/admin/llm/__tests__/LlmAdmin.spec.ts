import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import type { Component } from 'vue'
import { llmAPI } from '@/api/llm'
import { useLlmStore } from '@/stores/llm'
import LlmAdmin from '../LlmAdmin.vue'
import LlmProvidersPanel from '../LlmProvidersPanel.vue'
import LlmModelsPanel from '../LlmModelsPanel.vue'
import LlmPromptsPanel from '../LlmPromptsPanel.vue'
import LlmUsagePanel from '../LlmUsagePanel.vue'
import { call, vmOf } from '@/views/__tests__/vm'
import type { Schema } from '@/types/api'

const { showError, showSuccess, confirmMock } = vi.hoisted(() => ({
  showError: vi.fn(),
  showSuccess: vi.fn(),
  confirmMock: vi.fn()
}))
vi.mock('@/composables/useNotifications', () => ({ showError, showSuccess }))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))
vi.mock('@/stores/scopes', () => ({
  useScopesStore: () => ({
    scopes: [{ id: 's1', name: 'kidney' }],
    fetchUserScopes: vi.fn().mockResolvedValue([])
  })
}))
vi.mock('@/api/llm', () => ({
  llmAPI: Object.fromEntries(
    [
      'listProviders',
      'createProvider',
      'updateProvider',
      'setKey',
      'ping',
      'listModels',
      'createModel',
      'updateModel',
      'usage',
      'listRuns',
      'listTemplates',
      'createTemplate',
      'listVersions',
      'createVersion',
      'updateVersion',
      'publishVersion',
      'diffVersions'
    ].map(k => [k, vi.fn()])
  )
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
  has_key: true,
  key_fingerprint: 'ab12cd',
  created_at: '2026-10-01T00:00:00Z',
  ...over
})
const model: Schema<'ModelOut'> = {
  id: 'm1',
  provider_id: 'p1',
  model_id: 'claude-x-20250929',
  input_price_per_mtok_cents: '300',
  output_price_per_mtok_cents: '1500',
  max_tokens: 4096,
  timeout_s: 60,
  uses_max_completion_tokens: false,
  enabled: true,
  lock_version: 2
}
const version = (over: Partial<Schema<'VersionOut'>> = {}): Schema<'VersionOut'> => ({
  id: 'v1',
  template_id: 't1',
  version: 1,
  system_text: 'You are a skeptic.',
  user_text: 'Review {curation}',
  output_schema: { type: 'object' },
  few_shot_examples: [],
  sha256: 'f'.repeat(64),
  published_at: '2026-10-02T00:00:00Z',
  derived_from: null,
  lock_version: 1,
  created_at: '2026-10-01T00:00:00Z',
  ...over
})

let router: Router
async function mountPanel(component: Component) {
  router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }]
  })
  await router.push('/admin/llm')
  const w = mount(component, { attachTo: document.body, global: { plugins: [router] } })
  await flushPromises()
  return w
}

describe('LLM admin console', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
    confirmMock.mockResolvedValue(true)
    api.listProviders.mockResolvedValue([provider()])
    api.listModels.mockResolvedValue([model])
    api.listTemplates.mockResolvedValue([
      { id: 't1', key: 'skeptic', strategy: 'skeptic', description: null, created_at: '' }
    ])
  })

  it('loads the configuration on mount and opens on providers', async () => {
    const w = await mountPanel(LlmAdmin)
    expect(api.listProviders).toHaveBeenCalled()
    expect(w.text()).toContain('Providers and keys')
    expect(w.find('[data-test="key-status"]').text()).toContain('ab12cd')
  })

  it('creates a provider and warns that a new base URL deletes the key', async () => {
    const store = useLlmStore()
    store.providers = [provider()]
    const w = await mountPanel(LlmProvidersPanel)
    const vm = vmOf(w)

    call(vm, 'openEdit', null)
    Object.assign(vm.form as object, {
      name: ' OpenAI ',
      kind: 'openai_compatible',
      base_url: 'https://api.openai.com'
    })
    api.createProvider.mockResolvedValue(provider({ id: 'p2', name: 'OpenAI' }))
    await call(vm, 'save')
    expect(api.createProvider).toHaveBeenCalledWith({
      name: 'OpenAI',
      kind: 'openai_compatible',
      base_url: 'https://api.openai.com',
      enabled: true
    })

    call(vm, 'openEdit', store.providers[0])
    expect(vm.urlChangeDropsKey).toBe(false)
    ;(vm.form as { base_url: string }).base_url = 'https://other.example.com'
    await flushPromises()
    expect(vm.urlChangeDropsKey).toBe(true)
    expect(document.body.innerHTML).toContain('deletes the stored API key')
    api.updateProvider.mockRejectedValue(
      httpError(409, 'Changed by someone else; reload and retry')
    )
    await call(vm, 'save')
    expect(api.updateProvider).toHaveBeenCalledWith(
      'p1',
      expect.objectContaining({ lock_version: 1 })
    )
    expect(api.updateProvider.mock.calls[0]![1]).not.toHaveProperty('kind')
    expect(showError).toHaveBeenCalledWith(
      'Not saved, conflict: Changed by someone else; reload and retry'
    )
  })

  it('saves a key write-only: field cleared, never in the store, also on failure (#489)', async () => {
    const store = useLlmStore()
    store.providers = [provider({ has_key: false, key_fingerprint: null })]
    const w = await mountPanel(LlmProvidersPanel)
    const vm = vmOf(w)

    call(vm, 'openKey', store.providers[0])
    vm.apiKey = SECRET
    api.setKey.mockResolvedValue(undefined)
    api.listProviders.mockResolvedValue([provider()])
    await call(vm, 'saveKey')
    expect(api.setKey).toHaveBeenCalledWith('p1', { api_key: SECRET })
    expect(
      document.querySelector('[data-test="api-key-input"] input')?.getAttribute('autocomplete')
    ).toBe('new-password')
    expect(vm.apiKey).toBe('')
    expect(vm.showKey).toBe(false)
    expect(JSON.stringify(store.$state)).not.toContain(SECRET)
    expect(store.providers[0]!.key_fingerprint).toBe('ab12cd')

    call(vm, 'openKey', store.providers[0])
    vm.apiKey = SECRET
    api.setKey.mockRejectedValue(httpError(503, 'Audit log unavailable; change not saved'))
    await call(vm, 'saveKey')
    expect(showError).toHaveBeenCalledWith(
      'Not saved, service unavailable: Audit log unavailable; change not saved'
    )
    expect(vm.apiKey).toBe('')
    expect(JSON.stringify(store.$state)).not.toContain(SECRET)
  })

  it('test-pings a provider and reports success, provider errors and failures', async () => {
    useLlmStore().providers = [provider()]
    const vm = vmOf(await mountPanel(LlmProvidersPanel))
    api.ping.mockResolvedValueOnce({ ok: true, model: 'claude-x', latency_ms: 42 })
    await call(vm, 'ping', provider())
    expect(showSuccess).toHaveBeenCalledWith('Anthropic: claude-x answered in 42 ms')
    api.ping.mockResolvedValueOnce({
      ok: false,
      model: 'claude-x',
      latency_ms: 1,
      error_code: 'auth'
    })
    await call(vm, 'ping', provider())
    expect(showError).toHaveBeenCalledWith('Anthropic: ping failed (auth)')
    api.ping.mockRejectedValueOnce(httpError(422, 'Provider has no such model'))
    await call(vm, 'ping', provider())
    expect(showError).toHaveBeenLastCalledWith('Provider has no such model')
    expect(vm.pinging).toBeNull()
  })

  it('requires a pinned id for Anthropic providers only', async () => {
    const store = useLlmStore()
    store.providers = [provider(), { ...provider(), id: 'p2', kind: 'openai_compatible' }]
    const vm = vmOf(await mountPanel(LlmModelsPanel))
    call(vm, 'openEdit', null)
    const form = vm.form as { provider_id: string }
    form.provider_id = 'p1'
    expect(call(vm, 'dated', 'claude-sonnet-5-5')).toBe(true)
    expect(call(vm, 'dated', 'anthropic/claude-sonnet-5.5')).toContain('pinned')
    form.provider_id = 'p2'
    expect(call(vm, 'dated', 'anthropic/claude-sonnet-5.5')).toBe(true)
    expect(call(vm, 'dated', 'bad id')).toContain('only')
  })

  it('adds a dated model with prices and edits it with its revision', async () => {
    const store = useLlmStore()
    store.providers = [provider()]
    store.models = [model]
    const w = await mountPanel(LlmModelsPanel)
    const vm = vmOf(w)
    expect(w.text()).toContain('claude-x-20250929')
    expect(w.text()).toContain('Anthropic')

    call(vm, 'openEdit', null)
    Object.assign(vm.form as object, {
      provider_id: 'p1',
      model_id: ' gpt-4o-2024-08-06 ',
      uses_max_completion_tokens: true
    })
    api.createModel.mockResolvedValue({ ...model, id: 'm2', model_id: 'gpt-4o-2024-08-06' })
    await call(vm, 'save')
    expect(api.createModel).toHaveBeenCalledWith(
      expect.objectContaining({
        provider_id: 'p1',
        model_id: 'gpt-4o-2024-08-06',
        uses_max_completion_tokens: true
      })
    )

    call(vm, 'openEdit', model)
    await flushPromises()
    ;(vm.form as { max_tokens: unknown }).max_tokens = ''
    await call(vm, 'save')
    expect(api.updateModel).not.toHaveBeenCalled()
    ;(vm.form as { max_tokens: unknown }).max_tokens = 4096
    api.updateModel.mockResolvedValue({ ...model, lock_version: 3 })
    await call(vm, 'save')
    const sent = api.updateModel.mock.calls[0]![1]
    expect(sent.lock_version).toBe(2)
    expect(sent).not.toHaveProperty('model_id')
    api.updateModel.mockRejectedValue(httpError(503, 'cipher'))
    await call(vm, 'save')
    expect(showError).toHaveBeenCalledWith('Not saved, service unavailable: cipher')
  })

  it('keeps published prompt versions read-only, saves edits as drafts, publishes and diffs', async () => {
    const draft = version({ id: 'v2', version: 2, published_at: null, sha256: null })
    api.listVersions.mockResolvedValue([draft, version()])
    useLlmStore().templates = [
      { id: 't1', key: 'skeptic', strategy: 'skeptic', description: null, created_at: '' }
    ]
    const w = await mountPanel(LlmPromptsPanel)
    const vm = vmOf(w)
    vm.templateId = 't1'
    await flushPromises()
    expect(api.listVersions).toHaveBeenCalledWith('t1')
    expect(w.text()).toContain('Draft')

    call(vm, 'openEditor', version())
    expect(vm.readonly).toBe(true)
    vm.readonly = false
    ;(vm.draft as { system_text: string }).system_text = 'Be harsher.'
    api.updateVersion.mockResolvedValue(version({ id: 'v3', version: 3, published_at: null }))
    await call(vm, 'saveDraft')
    expect(api.updateVersion).toHaveBeenCalledWith('v1', {
      system_text: 'Be harsher.',
      user_text: 'Review {curation}',
      output_schema: { type: 'object' },
      few_shot_examples: [],
      lock_version: 1
    })
    expect(showSuccess).toHaveBeenCalledWith('Draft version 3 saved')

    call(vm, 'openEditor', null)
    expect(vm.canSave).toBe(false)
    Object.assign(vm.draft as object, { system_text: 's', user_text: 'u', output_schema: '[' })
    expect(vm.canSave).toBe(false)
    expect(call(vm, 'jsonError', 'output_schema')).toBe('Must be a JSON object')
    ;(vm.draft as { output_schema: string }).output_schema = '{}'
    ;(vm.draft as { few_shot_examples: string }).few_shot_examples = '{}'
    expect(call(vm, 'jsonError', 'few_shot_examples')).toBe('Must be a JSON array')
    ;(vm.draft as { few_shot_examples: string }).few_shot_examples = '[]'
    expect(vm.canSave).toBe(true)
    api.createVersion.mockRejectedValue(httpError(422, 'Unknown placeholder {x}'))
    await call(vm, 'saveDraft')
    expect(showError).toHaveBeenLastCalledWith('Unknown placeholder {x}')

    expect(w.find('[aria-label="Publish version 2"]').exists()).toBe(true)
    expect(w.find('[aria-label="View version 1"]').exists()).toBe(true)
    expect(w.find('[aria-label="Diff version 1"]').exists()).toBe(true)
    confirmMock.mockResolvedValueOnce(false)
    await call(vm, 'publish', draft)
    expect(api.publishVersion).not.toHaveBeenCalled()
    expect(confirmMock.mock.calls[0]![0].text).toContain('cannot be changed')
    api.publishVersion.mockResolvedValue({ ...draft, published_at: '2026-10-03T00:00:00Z' })
    await call(vm, 'publish', draft)
    expect(api.publishVersion).toHaveBeenCalledWith('v2', { lock_version: 1 })
    api.publishVersion.mockRejectedValue(httpError(409, 'Already published'))
    await call(vm, 'publish', draft)
    expect(showError).toHaveBeenLastCalledWith('Not saved, conflict: Already published')

    api.diffVersions.mockResolvedValue({
      from_id: 'v1',
      to_id: 'v2',
      system_diff: '-a\n+b\n',
      user_diff: '',
      output_schema_changed: true,
      few_shot_examples_changed: false
    })
    call(vm, 'openDiff', draft)
    await flushPromises()
    expect(api.diffVersions).toHaveBeenCalledWith('v2', 'v1')
    expect(document.querySelector('[data-test="system-diff"]')?.textContent).toContain('+b')
    expect(document.body.textContent).toContain('output schema')
    api.diffVersions.mockRejectedValue(httpError(404, 'Prompt version not found'))
    await call(vm, 'loadDiff')
    expect(showError).toHaveBeenLastCalledWith('Prompt version not found')
  })

  it('creates a prompt template and selects it', async () => {
    const vm = vmOf(await mountPanel(LlmPromptsPanel))
    Object.assign(vm.newTemplate as object, { key: 'Bad Key!', strategy: 'advocate' })
    await call(vm, 'createTemplate')
    expect(api.createTemplate).not.toHaveBeenCalled()
    Object.assign(vm.newTemplate as object, { key: ' advocate ', strategy: 'advocate' })
    api.createTemplate.mockResolvedValue({
      id: 't2',
      key: 'advocate',
      strategy: 'advocate',
      description: null,
      created_at: ''
    })
    api.listVersions.mockResolvedValue([])
    await call(vm, 'createTemplate')
    expect(api.createTemplate).toHaveBeenCalledWith(expect.objectContaining({ key: 'advocate' }))
    expect(vm.templateId).toBe('t2')
    api.createTemplate.mockRejectedValue(httpError(409, 'Template key exists'))
    ;(vm.newTemplate as { key: string }).key = 'advocate'
    await call(vm, 'createTemplate')
    expect(showError).toHaveBeenLastCalledWith('Not saved, conflict: Template key exists')
  })

  it('shows usage and runs per scope with cost in dollars', async () => {
    api.usage.mockResolvedValue([
      { scope_id: 's1', runs: 3, input_tokens: 1000, output_tokens: 200, cost_cents: '123.6' }
    ])
    api.listRuns.mockResolvedValue([
      {
        id: 'r1',
        curation_id: null,
        scope_id: 's1',
        strategy: 'skeptic',
        llm_model_id: 'm1',
        model_id: 'claude-x-20250929',
        prompt_version_id: 'v1',
        prompt_sha256: null,
        methodology_version_id: null,
        status: 'failed',
        input_tokens: 10,
        output_tokens: 0,
        cost_cents: '0',
        duration_ms: null,
        error_code: 'timeout',
        request_sha256: null,
        created_at: '2026-10-20T10:00:00Z',
        finished_at: null
      }
    ])
    const w = await mountPanel(LlmUsagePanel)
    expect(w.text()).toContain('kidney')
    expect(w.text()).toContain('$1.24')
    expect(w.text()).toContain('timeout')
  })
})
