import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LlmSecondView from '../LlmSecondView.vue'
import { llmAPI } from '@/api/llm'
import { call, vmOf } from '@/views/__tests__/vm'
import type { Schema } from '@/types/api'

const shownView = (w: { vm: unknown }) => vmOf(w).view as Schema<'SecondViewOut'>

const { showError } = vi.hoisted(() => ({ showError: vi.fn() }))
vi.mock('@/composables/useNotifications', () => ({ showError }))
vi.mock('@/api/llm', () => ({
  llmAPI: { secondView: vi.fn(), requestSecondView: vi.fn(), decideFinding: vi.fn() }
}))

const api = vi.mocked(llmAPI)

const finding = {
  id: 'f1',
  strategy: 'skeptic' as const,
  category: 'case_level',
  message: 'P1 is counted twice',
  citations: ['PMID:31000001'],
  decision: null,
  decided_at: null
}

const view = {
  curation_id: 'c1',
  enabled: true,
  pending: false,
  runs: [
    {
      strategy: 'skeptic' as const,
      run_id: 'r1',
      model_id: 'claude-sonnet-5-5',
      prompt_version: 2,
      methodology_version: 1,
      proposed_verdict: 'limited',
      status: 'succeeded',
      error_code: null as string | null,
      finished_at: null
    }
  ],
  findings: [finding],
  diff: [
    {
      category: 'classification',
      human: 'moderate',
      advocate: null,
      skeptic: 'limited',
      disagree: true
    },
    { category: 'total_score', human: 6.5, advocate: null, skeptic: 6.5, disagree: false }
  ]
}

async function mountView() {
  const w = mount(LlmSecondView, {
    props: { scopeId: 's1', curationId: 'c1' },
    attachTo: document.body
  })
  await flushPromises()
  return w
}

describe('LlmSecondView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.secondView.mockResolvedValue(structuredClone(view))
  })

  it('shows a failed run and its error code', async () => {
    const failed = structuredClone(view)
    failed.runs = failed.runs.map(r => ({ ...r, status: 'failed', error_code: 'invalid_output' }))
    api.secondView.mockResolvedValue(failed)
    const w = await mountView()
    vmOf(w).open = ['ai']
    await flushPromises()
    expect(w.text()).toContain('skeptic failed: invalid_output')
  })

  it('labels the AI output and counts disagreements', async () => {
    const w = await mountView()
    expect(api.secondView).toHaveBeenCalledWith('s1', 'c1')
    const vm = vmOf(w)
    expect(vm.disagreements).toBe(1)
    expect(w.text()).toContain('AI second view (advisory)')
    expect(w.text()).toContain('1 disagreement')
    expect(call(vm, 'shown', null)).toBe('-')
    expect(call(vm, 'shown', 6.5)).toBe(6.5)
  })

  it('names the collapsed header button, disagreements included (#530)', async () => {
    const w = await mountView()
    const header = w.get('button.v-expansion-panel-title')
    expect(header.attributes('aria-label')).toBe('AI second view (advisory), 1 disagreement')
  })

  it('says why when the feature is off and nothing ran, or the user may not see it', async () => {
    api.secondView.mockResolvedValue({ ...view, enabled: false, runs: [], findings: [], diff: [] })
    let w = await mountView()
    expect(w.find('[data-test="llm-second-view"]').exists()).toBe(false)
    expect(w.find('[data-test="second-view-off"]').exists()).toBe(true)
    api.secondView.mockRejectedValue({ response: { status: 403 } })
    w = await mountView()
    expect(w.find('[data-test="llm-second-view"]').exists()).toBe(false)
    expect(w.find('[data-test="second-view-off"]').exists()).toBe(true)
  })

  it('records accept and dismiss per finding', async () => {
    const w = await mountView()
    api.decideFinding.mockResolvedValue({ ...finding, decision: 'dismissed' })
    await call(vmOf(w), 'decide', 'f1', 'dismissed')
    expect(api.decideFinding).toHaveBeenCalledWith('f1', { decision: 'dismissed' })
    expect(shownView(w).findings[0]?.decision).toBe('dismissed')
    api.decideFinding.mockRejectedValue({ response: { status: 403, data: { detail: 'no' } } })
    await call(vmOf(w), 'decide', 'f1', 'accepted')
    expect(showError).toHaveBeenCalled()
  })

  it('requests a run and reports a refusal', async () => {
    const w = await mountView()
    api.requestSecondView.mockResolvedValue({ ...view, pending: true })
    await call(vmOf(w), 'request')
    expect(shownView(w).pending).toBe(true)
    api.requestSecondView.mockRejectedValue({
      response: { status: 422, data: { detail: 'daily_run_cap' } }
    })
    await call(vmOf(w), 'request')
    expect(showError).toHaveBeenCalled()
  })

  it('shows the labelled runs, the diff and the findings when opened', async () => {
    const w = await mountView()
    vmOf(w).open = ['ai']
    await flushPromises()
    const text = w.text()
    expect(text).toContain('skeptic: claude-sonnet-5-5, prompt v2, methodology v1')
    expect(w.findAll('[data-test="diff-row"]')).toHaveLength(2)
    expect(text).toContain('P1 is counted twice')
    expect(text).toContain('Cites: PMID:31000001')
    api.decideFinding.mockResolvedValue({ ...finding, decision: 'accepted' })
    const accept = w.findAll('button').find(b => b.text() === 'Accept')
    await accept?.trigger('click')
    await flushPromises()
    expect(api.decideFinding).toHaveBeenCalledWith('f1', { decision: 'accepted' })
    api.requestSecondView.mockResolvedValue({ ...view, pending: true, findings: [] })
    await w.find('[data-test="request-second-view"]').trigger('click')
    await flushPromises()
    api.secondView.mockResolvedValue({ ...view, runs: [], findings: [], diff: [] })
    await w.find('[data-test="refresh-second-view"]').trigger('click')
    await flushPromises()
    expect(w.text()).toContain('Run second view')
  })
})
