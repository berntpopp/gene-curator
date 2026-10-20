import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useScopesStore } from '@/stores/scopes'
import { useAuthStore } from '@/stores/auth'
import { useCurationsStore } from '@/stores/curations'
import { useNotificationsStore } from '@/stores/notifications'
import CurationList from '../CurationList.vue'

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock })
}))

const rows = [
  {
    id: 'c1',
    gene_symbol: 'HNF1B',
    disease_name: 'Renal cysts',
    created_by: 'u1',
    curator_name: 'Ada',
    status: 'draft',
    computed_verdict: 'Definitive',
    computed_scores: { total_score: 12 },
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 'c2',
    gene_symbol: 'PKD1',
    disease_name: 'Polycystic kidney',
    created_by: 'u2',
    curator_name: 'Grace',
    status: 'approved',
    computed_verdict: null,
    computed_scores: { total_score: 3 },
    updated_at: '2024-01-02T00:00:00Z'
  }
]

function setup(
  user: { role: string; id: string } | null,
  curations = rows,
  scopeRole: 'admin' | 'curator' | 'reviewer' | 'viewer' | null = 'curator'
) {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  auth.user = user as typeof auth.user
  useScopesStore().currentUserRole = scopeRole
  const store = useCurationsStore()
  store.curations = curations as unknown as typeof store.curations
  store.loading = false
  const fetch = vi.spyOn(store, 'fetchCurations').mockResolvedValue(undefined as never)
  vi.spyOn(store, 'updateFilters').mockImplementation(() => undefined)
  const remove = vi.spyOn(store, 'deleteCuration').mockResolvedValue(undefined as never)
  const notifications = useNotificationsStore()
  const toast = vi.spyOn(notifications, 'addToast').mockImplementation(() => undefined as never)
  const wrapper = mount(CurationList, {
    props: { scopeId: 'scope-1' },
    global: { plugins: [] }
  })
  return { wrapper, store, fetch, remove, toast }
}

describe('CurationList', () => {
  beforeEach(() => {
    pushMock.mockReset()
    vi.restoreAllMocks()
  })

  it('loads the scope curations on mount', async () => {
    const { fetch, store } = setup({ role: 'curator', id: 'u1' })
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith({ scope_id: 'scope-1' })
    expect(store.curations).toHaveLength(2)
  })

  it('renders one table row per curation with gene, classification and score', async () => {
    const { wrapper } = setup({ role: 'curator', id: 'u1' })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('HNF1B')
    expect(text).toContain('PKD1')
    expect(text).toContain('Definitive')
    expect(text).toContain('12')
    expect(text).toContain('Grace')
  })

  it('filters by gene or disease text, case-insensitively', async () => {
    const { wrapper } = setup({ role: 'curator', id: 'u1' })
    await flushPromises()
    await wrapper.find('input').setValue('POLYCYSTIC')
    expect(wrapper.text()).toContain('PKD1')
    expect(wrapper.text()).not.toContain('HNF1B')
  })

  it('shows the no-match message and clears filters on request', async () => {
    const { wrapper } = setup({ role: 'curator', id: 'u1' })
    await flushPromises()
    await wrapper.find('input').setValue('nothing matches')
    expect(wrapper.text()).toContain('No curations match your filters')

    const clear = wrapper.findAll('button').find(b => b.text().includes('Clear Filters'))
    await clear?.trigger('click')
    expect(wrapper.text()).toContain('HNF1B')
  })

  it('shows the empty state for a scope without curations', async () => {
    const { wrapper } = setup({ role: 'user', id: 'u9' }, [], 'viewer')
    await flushPromises()
    expect(wrapper.text()).toContain('No curations yet')
    expect(wrapper.text()).not.toContain('Start Curation')
  })

  it('offers Start Curation by scope role, not application role', async () => {
    const curator = setup({ role: 'user', id: 'u1' }, rows, 'curator')
    await flushPromises()
    expect(curator.wrapper.text()).toContain('Start Curation')

    const viewer = setup({ role: 'user', id: 'u1' }, rows, 'viewer')
    await flushPromises()
    expect(viewer.wrapper.text()).not.toContain('Start Curation')
  })

  it('switches to card view and shows the score per card', async () => {
    const { wrapper } = setup({ role: 'curator', id: 'u1' })
    await flushPromises()
    await wrapper.findComponent({ name: 'VBtnToggle' }).vm.$emit('update:modelValue', 'cards')
    await flushPromises()
    expect(wrapper.text()).toContain('ClinGen Score')
    expect(wrapper.text()).toContain('/ 18 points')
  })
})
