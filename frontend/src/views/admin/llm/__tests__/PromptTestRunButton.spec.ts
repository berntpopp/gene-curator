import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { llmAPI } from '@/api/llm'
import { useLlmStore, type PromptVersion } from '@/stores/llm'
import PromptTestRunButton from '../PromptTestRunButton.vue'
import { call, vmOf } from '@/views/__tests__/vm'

const { showError } = vi.hoisted(() => ({ showError: vi.fn() }))
vi.mock('@/composables/useNotifications', () => ({ showError, showSuccess: vi.fn() }))
vi.mock('@/api/llm', () => ({ llmAPI: { testRun: vi.fn() } }))

const api = vi.mocked(llmAPI)
const version = { id: 'v1', version: 3 } as PromptVersion

function mountButton() {
  const store = useLlmStore()
  store.models = [
    { id: 'off', model_id: 'old-20240101', enabled: false },
    { id: 'm1', model_id: 'claude-x-20250929', enabled: true }
  ] as typeof store.models
  return mount(PromptTestRunButton, { props: { version }, attachTo: document.body })
}

describe('PromptTestRunButton', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('runs the version over the golden set with the first enabled model and shows results', async () => {
    api.testRun.mockResolvedValueOnce({
      model: 'claude-x-20250929',
      passed: 1,
      total: 2,
      cases: [
        { case: 'strong', ok: true, error_code: null, input_tokens: 10, output_tokens: 5 },
        {
          case: 'refuted',
          ok: false,
          error_code: 'invalid_output',
          input_tokens: 9,
          output_tokens: 1
        }
      ]
    })
    const w = mountButton()
    await w.find('button').trigger('click')
    await call(vmOf(w), 'run')
    await flushPromises()

    expect(api.testRun).toHaveBeenCalledWith('v1', { model_id: 'm1' })
    const text = document.body.textContent ?? ''
    expect(text).toContain('1 of 2 cases passed with claude-x-20250929')
    expect(text).toContain('invalid_output')
    expect(vmOf(w).running).toBe(false)
    w.unmount()
  })

  it('reports a failed test run', async () => {
    api.testRun.mockRejectedValueOnce({
      response: { status: 503, data: { detail: 'Golden set not installed' } }
    })
    const w = mountButton()
    await call(vmOf(w), 'run')
    expect(showError).toHaveBeenCalledWith('Golden set not installed')
    expect(vmOf(w).result).toBeNull()
    w.unmount()
  })
})
