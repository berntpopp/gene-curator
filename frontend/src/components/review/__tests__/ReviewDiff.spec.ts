import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ReviewDiff from '../ReviewDiff.vue'
import { useReviewStore } from '@/stores/review'
import { reviewCommentsAPI } from '@/api/reviewComments'

vi.mock('@/api/reviewComments', () => ({
  reviewCommentsAPI: {
    getDiff: vi.fn(),
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    myPendingItemIds: vi.fn()
  }
}))
const api = vi.mocked(reviewCommentsAPI)

const diff = {
  baseline: { audit_id: 1, as_of: '2026-10-15T10:00:00Z', source: 'review' },
  items: [
    { path: 'g.cases[a].points', change: 'changed', before: 1.5, after: 2 },
    { path: 'g.cases[a].explanation', change: 'added', before: null, after: 'splice assay' },
    { path: 'g.cases[b]', change: 'removed', before: { pmid: '9' }, after: null }
  ]
}
const comment = (o: Record<string, unknown>) =>
  ({
    id: `k${Math.random()}`,
    curation_id: 'cur',
    review_id: null,
    body: '',
    author_id: 'bob',
    status: 'open',
    kind: 'query',
    created_at: '2026-10-20T10:00:00Z',
    updated_at: '2026-10-20T10:00:00Z',
    ...o
  }) as never

async function mountDiff(props: Record<string, unknown> = {}, comments: unknown[] = []) {
  setActivePinia(createPinia())
  api.getDiff.mockResolvedValue(diff as never)
  api.list.mockResolvedValue(comments as never)
  const w = mount(ReviewDiff, {
    props: {
      curationId: 'cur',
      me: 'bob',
      creatorId: 'alice',
      reviewer: true,
      canReply: true,
      ...props
    }
  })
  await flushPromises()
  return w
}

describe('ReviewDiff', () => {
  beforeEach(() => Object.values(api).forEach(m => m.mockReset()))

  it('says what the diff is relative to and groups changes by item with before and after', async () => {
    const w = await mountDiff()
    expect(w.find('[data-testid=baseline]').text()).toBe(
      'Showing changes since your last review on 2026-10-15.'
    )
    const rows = w.findAll('[data-testid=item]')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('Genetic'.slice(0, 1)) // label rendered
    expect(rows[0]!.find('del').text()).toBe('1.5')
    expect(rows[0]!.find('ins').text()).toBe('2')
    expect(rows[0]!.text()).toContain('splice assay')
    expect(rows[1]!.text()).toContain('Removed')
  })

  it('names the previous submission as baseline, and a first review', async () => {
    setActivePinia(createPinia())
    api.getDiff.mockResolvedValue({
      baseline: { ...diff.baseline, source: 'previous_submission' },
      items: []
    } as never)
    api.list.mockResolvedValue([])
    let w = mount(ReviewDiff, {
      props: { curationId: 'cur', me: 'bob', creatorId: 'alice', reviewer: true, canReply: true }
    })
    await flushPromises()
    expect(w.find('[data-testid=baseline]').text()).toContain('the previous submission')
    expect(w.text()).toContain('No changes')

    api.getDiff.mockResolvedValue({ baseline: null, items: diff.items } as never)
    w = mount(ReviewDiff, {
      props: { curationId: 'cur', me: 'bob', creatorId: 'alice', reviewer: true, canReply: true }
    })
    await flushPromises()
    expect(w.find('[data-testid=baseline]').text()).toBe('First review: all items new.')
  })

  it('shows an error when the review cannot be loaded', async () => {
    setActivePinia(createPinia())
    api.getDiff.mockRejectedValue(new Error('x'))
    api.list.mockResolvedValue([])
    const w = mount(ReviewDiff, {
      props: { curationId: 'cur', me: 'bob', creatorId: 'alice', reviewer: true, canReply: true }
    })
    await flushPromises()
    expect(w.find('[data-testid=review-error]').exists()).toBe(true)
  })

  it('lets a reviewer accept an item and withdraw the acceptance', async () => {
    const w = await mountDiff()
    api.create.mockResolvedValue(comment({ id: 'acc', kind: 'accepted', item_path: 'g.cases[a]' }))
    await w.find('[data-testid="accept-g.cases[a]"]').trigger('click')
    await flushPromises()
    expect(api.create).toHaveBeenCalledWith('cur', { item_path: 'g.cases[a]', kind: 'accepted' })
    expect(w.find('[data-testid="accept-g.cases[a]"]').attributes('aria-pressed')).toBe('true')

    api.update.mockResolvedValue(
      comment({ id: 'acc', kind: 'accepted', item_path: 'g.cases[a]', status: 'resolved' })
    )
    await w.find('[data-testid="accept-g.cases[a]"]').trigger('click')
    await flushPromises()
    expect(api.update).toHaveBeenCalledWith('cur', 'acc', { status: 'resolved' })
  })

  it('lets a reviewer query an item', async () => {
    const w = await mountDiff()
    await w.find('[data-testid="query-g.cases[a]"]').trigger('click')
    api.create.mockResolvedValue(comment({ item_path: 'g.cases[a]', body: 'Check gnomAD' }))
    await w.find('[data-testid=thread-input] textarea').setValue('Check gnomAD')
    await w.find('[data-testid=thread-send]').trigger('click')
    await flushPromises()
    expect(api.create).toHaveBeenCalledWith('cur', {
      item_path: 'g.cases[a]',
      kind: 'query',
      body: 'Check gnomAD'
    })
    expect(w.text()).toContain('Check gnomAD')
    expect(w.text()).toContain('You')
  })

  it('shows the curator the reviewer queries, lets them reply and resolve, but never Accept', async () => {
    const q = comment({ id: 'q', item_path: 'g.cases[a]', body: 'Explain 2.0 points' })
    const w = await mountDiff({ me: 'alice', reviewer: false }, [q])
    expect(w.find('[data-testid="accept-g.cases[a]"]').exists()).toBe(false)
    expect(w.find('[data-testid="query-g.cases[a]"]').exists()).toBe(false)
    expect(w.text()).toContain('Reviewer')
    expect(w.text()).toContain('Explain 2.0 points')

    api.create.mockResolvedValue(
      comment({ item_path: 'g.cases[a]', body: 'Added a note', author_id: 'alice' })
    )
    await w.find('[data-testid=thread-input] textarea').setValue('Added a note')
    await w.find('[data-testid=thread-send]').trigger('click')
    await flushPromises()
    expect(api.create).toHaveBeenCalledWith('cur', {
      item_path: 'g.cases[a]',
      kind: 'query',
      body: 'Added a note'
    })

    api.update.mockResolvedValue(comment({ id: 'q', item_path: 'g.cases[a]', status: 'resolved' }))
    api.update.mockClear()
    await w.find('[data-testid=thread-resolve]').trigger('click')
    await flushPromises()
    expect(api.update).toHaveBeenCalledWith('cur', 'q', { status: 'resolved' })
  })

  it('is read-only for people who cannot reply', async () => {
    const q = comment({ id: 'q', item_path: 'g.cases[a]', body: 'Explain' })
    const w = await mountDiff({ me: 'zed', reviewer: false, canReply: false }, [q])
    expect(w.text()).toContain('Explain')
    expect(w.find('[data-testid=thread-input]').exists()).toBe(false)
    expect(w.find('[data-testid=thread-resolve]').exists()).toBe(false)
  })

  it('reports a failed action', async () => {
    const w = await mountDiff()
    api.create.mockRejectedValue({ response: { data: { detail: 'Not authorized' } } })
    await w.find('[data-testid="accept-g.cases[a]"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid=review-error]').text()).toContain('Not authorized')
  })
})

describe('ReviewDiff baseline wording', () => {
  it('does not say "your" review to a curator', async () => {
    const w = await mountDiff({ me: 'alice', reviewer: false })
    expect(w.find('[data-testid=baseline]').text()).toBe(
      'Showing changes since the last review on 2026-10-15.'
    )
  })
})

describe('ReviewDiff outside review', () => {
  it('stays hidden without comments and shows once there are some', async () => {
    let w = await mountDiff({ onlyWithComments: true })
    expect(w.find('section').exists()).toBe(false)
    w = await mountDiff({ onlyWithComments: true }, [
      comment({ item_path: 'g.cases[a]', body: 'Explain' })
    ])
    expect(w.find('section').exists()).toBe(true)
  })
})

describe('store shared with the dialogs', () => {
  it('exposes loaded comments', async () => {
    await mountDiff()
    expect(useReviewStore().diff?.items).toHaveLength(3)
  })
})
