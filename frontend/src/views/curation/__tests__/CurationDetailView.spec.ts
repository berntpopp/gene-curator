import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  curationsAPI: { getCuration: vi.fn() },
  workflowAPI: { transitionCuration: vi.fn() },
  schemasAPI: { getWorkflowPairById: vi.fn() }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: { scopeId: 'sc1', curationId: 'c1' } })
}))

import { curationsAPI } from '@/api'
import CurationDetailView from '@/views/curation/CurationDetailView.vue'

describe('CurationDetailView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(curationsAPI.getCuration).mockReset()
  })

  it('shows a loading card while the curation is fetched', async () => {
    vi.mocked(curationsAPI.getCuration).mockReturnValue(new Promise(() => {}))
    const wrapper = mount(CurationDetailView, { global: { stubs: { DynamicForm: true } } })
    await flushPromises()
    expect(curationsAPI.getCuration).toHaveBeenCalledWith('c1')
    expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
  })

  it('shows an error message when the curation cannot be loaded', async () => {
    vi.mocked(curationsAPI.getCuration).mockRejectedValue(new Error('500'))
    const wrapper = mount(CurationDetailView, { global: { stubs: { DynamicForm: true } } })
    await flushPromises()
    expect(wrapper.text()).toContain('Failed to load curation details')
  })
})
