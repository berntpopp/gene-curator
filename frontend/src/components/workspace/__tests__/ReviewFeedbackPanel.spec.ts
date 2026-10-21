import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ReviewFeedbackPanel from '../ReviewFeedbackPanel.vue'
import { useReviewFeedbackStore } from '@/stores/reviewFeedback'

const mountPanel = async (
  fb: { note: string | null; queries: unknown[]; any: boolean } | Error
) => {
  setActivePinia(createPinia())
  const fetch = vi.spyOn(useReviewFeedbackStore(), 'fetch')
  if (fb instanceof Error) fetch.mockRejectedValue(fb)
  else fetch.mockResolvedValue(fb as never)
  const w = mount(ReviewFeedbackPanel, {
    props: { curationId: 'c1', scopeId: 's1', me: 'alice' },
    global: { stubs: { RouterLink: RouterLinkStub } }
  })
  await flushPromises()
  return { w, fetch }
}

describe('ReviewFeedbackPanel', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('shows the reviewer note and open queries with the item they are about', async () => {
    const { w, fetch } = await mountPanel({
      note: 'Please add the segregation data',
      queries: [
        { id: 'q', item_path: 'genetic_evidence.case_level[a]', body: 'Explain 2.0 points' }
      ],
      any: true
    })
    expect(fetch).toHaveBeenCalledWith('c1', 'alice')
    expect(w.find('[data-testid=feedback-note]').text()).toContain(
      'Please add the segregation data'
    )
    expect(w.find('[data-testid=feedback-query]').text()).toContain(
      'Genetic evidence › Case level [a]'
    )
    expect(w.find('[data-testid=feedback-query]').text()).toContain('Explain 2.0 points')
    expect(w.findComponent(RouterLinkStub).props('to')).toBe('/scopes/s1/curations/c1')
  })

  it('renders nothing without feedback or when it cannot be loaded', async () => {
    expect(
      (await mountPanel({ note: null, queries: [], any: false })).w.find('aside').exists()
    ).toBe(false)
    expect((await mountPanel(new Error('x'))).w.find('aside').exists()).toBe(false)
  })

  it('shows only the note when there are no queries', async () => {
    const { w } = await mountPanel({ note: 'Fix it', queries: [], any: true })
    expect(w.find('[data-testid=feedback-note]').exists()).toBe(true)
    expect(w.find('[data-testid=feedback-query]').exists()).toBe(false)
  })
})
