import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DynamicForm from '../DynamicForm.vue'
import { validationAPI } from '@/api/validation'

vi.mock('@/api/validation', () => ({ validationAPI: { validateEvidence: vi.fn() } }))
const reply: Awaited<ReturnType<typeof validationAPI.validateEvidence>> = {
  is_valid: true,
  errors: [],
  warnings: [],
  field_validations: {},
  business_rule_violations: [],
  completeness_score: 1,
  required_fields_missing: [],
  suggested_improvements: [],
  score_calculations: { total_score: 7.5, verdict: 'Current' }
}
let wrapper: VueWrapper
beforeEach(() => {
  setActivePinia(createPinia())
  vi.useFakeTimers()
  vi.mocked(validationAPI.validateEvidence).mockReset().mockResolvedValue(reply)
})
afterEach(() => {
  wrapper?.unmount()
  vi.useRealTimers()
})
async function render() {
  wrapper = mount(DynamicForm, {
    props: {
      schemaId: 'test',
      initialData: { note: 'Initial' },
      hideActions: true,
      definition: {
        field_definitions: { note: { type: 'string', title: 'Note' } },
        scoring_configuration: { engine: 'custom' }
      }
    }
  })
  await flushPromises()
  expect(wrapper.text()).toContain('Current')
}
const pending = () => wrapper.emitted('validation-pending')?.at(-1)?.[0]
it('shows a skeleton throughout debounce, then the latest score without an unavailable flash', async () => {
  await render()
  await wrapper.get('input').setValue('Edited')
  expect(wrapper.find('.v-skeleton-loader').exists()).toBe(true)
  expect(pending()).toBe(true)
  expect(wrapper.text()).not.toContain('Current')
  expect(wrapper.text()).not.toContain('unavailable')
  await vi.advanceTimersByTimeAsync(499)
  expect(wrapper.find('.v-skeleton-loader').exists()).toBe(true)
  await vi.advanceTimersByTimeAsync(1)
  await flushPromises()
  expect(pending()).toBe(false)
  expect(wrapper.find('.v-skeleton-loader').exists()).toBe(false)
  expect(wrapper.text()).toContain('Current')
})
it.each(['resolve', 'reject'] as const)(
  'an old request that %ss cannot clear the newer edit pending state',
  async outcome => {
    await render()
    let finish!: (value: typeof reply) => void
    let fail!: (error: Error) => void
    vi.mocked(validationAPI.validateEvidence).mockReturnValueOnce(
      new Promise((resolve, reject) => {
        finish = resolve
        fail = reject
      })
    )
    await wrapper.get('input').setValue('First edit')
    await vi.advanceTimersByTimeAsync(500)
    await wrapper.get('input').setValue('Second edit')
    if (outcome === 'resolve')
      finish({ ...reply, score_calculations: { total_score: 99, verdict: 'Stale' } })
    else fail(new Error('Old request failed'))
    await flushPromises()
    expect(pending()).toBe(true)
    expect(wrapper.find('.v-skeleton-loader').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Stale')
    expect(wrapper.text()).not.toContain('unavailable')
    await vi.advanceTimersByTimeAsync(500)
    await flushPromises()
    expect(pending()).toBe(false)
    expect(wrapper.text()).toContain('Current')
  }
)
it('ends pending after the current request fails without restoring stale numbers', async () => {
  await render()
  vi.mocked(validationAPI.validateEvidence).mockRejectedValueOnce(new Error('Network unavailable'))
  await wrapper.get('input').setValue('Edited')
  await vi.advanceTimersByTimeAsync(500)
  await flushPromises()
  expect(pending()).toBe(false)
  expect(wrapper.find('.v-skeleton-loader').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('Current')
})
