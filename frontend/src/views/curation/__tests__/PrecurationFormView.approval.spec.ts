import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// #530: an approval that creates no curation says why and links the blocking curation
vi.mock('@/api', () => ({
  genesAPI: { getGeneById: vi.fn().mockResolvedValue({ approved_symbol: 'PKD1' }) },
  scopesAPI: { getScopeById: vi.fn().mockResolvedValue({}) },
  schemasAPI: { getWorkflowPairs: vi.fn().mockResolvedValue([]) }
}))
const push = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ params: { scopeId: 'sc1', precurationId: 'p1' }, query: {} })
}))
vi.mock('@/api/precurations', () => ({
  precurationsAPI: {
    getPrecuration: vi.fn().mockResolvedValue({
      id: 'p1',
      gene_id: 'g1',
      scope_id: 'sc1',
      status: 'submitted',
      created_by: 'alice'
    }),
    approvePrecuration: vi.fn(),
    rejectPrecuration: vi.fn()
  }
}))
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn().mockResolvedValue(true) })
}))

import { precurationsAPI } from '@/api/precurations'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import { useWorkCountsStore } from '@/stores/workCounts'
import PrecurationFormView from '@/views/curation/PrecurationFormView.vue'

async function approveWith(result: Record<string, unknown>) {
  vi.mocked(precurationsAPI.approvePrecuration).mockResolvedValue(result as never)
  const wrapper = mount(PrecurationFormView, {
    global: {
      stubs: {
        SchemaDrivenPrecurationForm: true,
        'router-link': { props: ['to'], template: '<a :href="to"><slot /></a>' }
      }
    }
  })
  await flushPromises()
  await wrapper.find('[data-testid="approve-precuration"]').trigger('click')
  await flushPromises()
  return wrapper
}

describe('PrecurationFormView approval result', () => {
  beforeEach(() => {
    push.mockReset()
    setActivePinia(createPinia())
    useAuthStore().user = { id: 'bob' } as never
    vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('reviewer' as never)
    vi.spyOn(useWorkCountsStore(), 'fetch').mockResolvedValue(undefined)
  })

  it('stays and links the open curation that blocked a new one', async () => {
    const message = 'Precuration approved; no curation created: Open curation c9 covers'
    const wrapper = await approveWith({ curation_created: false, curation_id: 'c9', message })
    const notice = wrapper.find('[data-test="approval-notice"]')
    expect(notice.text()).toContain(message)
    expect(notice.find('a').attributes('href')).toBe('/scopes/sc1/curations/c9')
    expect(push).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="approve-precuration"]').exists()).toBe(false)
  })

  it('returns to the queue when the approval created the curation', async () => {
    const wrapper = await approveWith({ curation_created: true, curation_id: 'c1', message: 'ok' })
    expect(wrapper.find('[data-test="approval-notice"]').exists()).toBe(false)
    expect(push).toHaveBeenCalledWith({ name: 'review-queue' })
  })
})
