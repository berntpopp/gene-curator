import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ScopeLlmSettings from '../ScopeLlmSettings.vue'
import { llmAPI } from '@/api/llm'
import { call, vmOf } from '@/views/__tests__/vm'

const { showError, showSuccess } = vi.hoisted(() => ({ showError: vi.fn(), showSuccess: vi.fn() }))
vi.mock('@/composables/useNotifications', () => ({ showError, showSuccess }))
vi.mock('@/api/llm', () => ({
  llmAPI: { scopeOptions: vi.fn(), scopeSettings: vi.fn(), saveScopeSettings: vi.fn() }
}))

const api = vi.mocked(llmAPI)
const httpError = (status: number, detail: string) => ({ response: { status, data: { detail } } })

const saved = {
  scope_id: 's1',
  enabled: false,
  monthly_token_cap: 0,
  monthly_cost_cap_cents: 0,
  daily_run_cap: 0,
  lock_version: 0
}

const options = {
  models: [{ id: 'm1', model_id: 'claude-x-20250929', provider_name: 'Anthropic' }],
  prompt_versions: [
    { id: 'v1', template_key: 'skeptic', strategy: 'skeptic' as const, version: 2 },
    { id: 'v2', template_key: 'advocate', strategy: 'advocate' as const, version: 1 }
  ]
}

async function mountPanel() {
  const w = mount(ScopeLlmSettings, { props: { scopeId: 's1' }, attachTo: document.body })
  await flushPromises()
  return w
}

describe('ScopeLlmSettings', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.scopeOptions.mockResolvedValue(options)
    api.scopeSettings.mockResolvedValue(saved)
  })

  it('offers only enabled models and published versions per strategy, never key data', async () => {
    const w = await mountPanel()
    const vm = vmOf(w)
    expect(vm.modelItems).toEqual([{ title: 'claude-x-20250929 (Anthropic)', value: 'm1' }])
    expect(call(vm, 'promptItems', 'skeptic')).toEqual([{ title: 'skeptic v2', value: 'v1' }])
    expect(vm.form).toEqual({
      lock_version: 0,
      enabled: false,
      model_id: null,
      skeptic_prompt_version_id: null,
      advocate_prompt_version_id: null,
      monthly_token_cap: 0,
      monthly_cost_cap_cents: 0,
      daily_run_cap: 0
    })
    expect(w.text()).not.toMatch(/fingerprint|api key/i)
  })

  it('needs a model to enable, saves with the revision and shows a stale save', async () => {
    const vm = vmOf(await mountPanel())
    const form = vm.form as Record<string, unknown>
    form.enabled = true
    await flushPromises()
    expect(document.body.textContent).toContain('Enabling requires a model')

    Object.assign(form, { model_id: 'm1', daily_run_cap: 5 })
    api.saveScopeSettings.mockResolvedValue({
      ...saved,
      enabled: true,
      model_id: 'm1',
      daily_run_cap: 5,
      lock_version: 1
    })
    await call(vm, 'save')
    expect(api.saveScopeSettings).toHaveBeenCalledWith(
      's1',
      expect.objectContaining({ enabled: true, model_id: 'm1', daily_run_cap: 5, lock_version: 0 })
    )
    expect((vm.form as { lock_version: number }).lock_version).toBe(1)
    expect(showSuccess).toHaveBeenCalledWith('LLM settings saved')

    api.saveScopeSettings.mockRejectedValue(
      httpError(409, 'Changed by someone else; reload and retry')
    )
    await call(vm, 'save')
    expect(showError).toHaveBeenCalledWith(
      'Not saved, conflict: Changed by someone else; reload and retry'
    )
  })

  it('shows a load failure', async () => {
    api.scopeSettings.mockRejectedValue(httpError(403, 'Scope admin role required'))
    const w = await mountPanel()
    expect(w.text()).toContain('Scope admin role required')
  })

  it('flags a saved model that was disabled since and blocks save until it is replaced', async () => {
    api.scopeSettings.mockResolvedValue({ ...saved, model_id: 'gone' })
    const vm = vmOf(await mountPanel())
    expect(document.body.textContent).toContain('The saved model is no longer available')
    expect(vm.canSave).toBe(false)
    await call(vm, 'save')
    expect(api.saveScopeSettings).not.toHaveBeenCalled()
    ;(vm.form as { model_id: string | null }).model_id = null
    expect(vm.canSave).toBe(true)
  })

  it('never sends an empty or out-of-range cap', async () => {
    const vm = vmOf(await mountPanel())
    const form = vm.form as Record<string, unknown>
    form.daily_run_cap = ''
    expect(vm.canSave).toBe(false)
    form.daily_run_cap = 10 ** 7
    expect(vm.canSave).toBe(false)
    await call(vm, 'save')
    expect(api.saveScopeSettings).not.toHaveBeenCalled()
    form.daily_run_cap = 3
    expect(vm.canSave).toBe(true)
  })
})
