/**
 * Behaviour tests for the ScopeCreate and ScopeDashboard views.
 * The scopes store is real; its actions are stubbed with vi.spyOn.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { call, vmOf } from '@/views/__tests__/vm'
import ScopeCreate from '@/views/scope/ScopeCreate.vue'
import ScopeDashboard from '@/views/scope/ScopeDashboard.vue'
import { useScopesStore } from '@/stores/scopes'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/users'
import { snackbarState } from '@/composables/useNotifications'

const { routerPush, routerReplace, routerBack, routeState, logger } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routerReplace: vi.fn(),
  routerBack: vi.fn(),
  routeState: { params: {} as Record<string, string>, query: {} as Record<string, string> },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: routerPush, replace: routerReplace, back: routerBack }),
  useRoute: () => routeState
}))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/api/users', () => ({ usersApi: { searchUsers: vi.fn() } }))
vi.mock('@/api/schemas', () => ({
  schemasAPI: {
    getWorkflowPairs: vi.fn().mockResolvedValue([
      {
        id: 'wp-1',
        name: 'ClinGen',
        version: '11',
        precuration_schema_id: 'a',
        curation_schema_id: 'b'
      }
    ]),
    getSchemas: vi.fn().mockResolvedValue([])
  }
}))

let pinia: ReturnType<typeof createPinia>
const opts = () => ({
  attachTo: document.body,
  global: {
    plugins: [pinia],
    stubs: {
      RouterLink: RouterLinkStub,
      ScopeOverview: true,
      GeneList: true,
      CurationList: true,
      ScopeSettings: true,
      MemberManagement: true
    }
  }
})

beforeEach(() => {
  vi.clearAllMocks()
  pinia = createPinia()
  setActivePinia(pinia)
  routeState.params = {}
})

afterEach(() => {
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('ScopeCreate', () => {
  const mountView = async () => {
    const store = useScopesStore()
    const fetchUserScopes = vi.spyOn(store, 'fetchUserScopes').mockResolvedValue(undefined as never)
    const wrapper = mount(ScopeCreate, opts())
    await flushPromises()
    return { wrapper, store, fetchUserScopes, vm: vmOf(wrapper) }
  }

  it('loads existing scopes for name validation when none are loaded', async () => {
    const { fetchUserScopes } = await mountView()
    expect(fetchUserScopes).toHaveBeenCalled()
  })

  it('keeps going when the existing scopes cannot be loaded', async () => {
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockRejectedValue(new Error('down'))
    mount(ScopeCreate, opts())
    await flushPromises()
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to load existing scopes',
      expect.objectContaining({ error: 'down' })
    )
  })

  it('warns when the typed scope name already exists', async () => {
    const { store, vm } = await mountView()
    store.scopes = [{ id: 's1', name: 'kidney-genetics' }] as never
    ;(vm.scopeData as { name: string }).name = 'kidney-genetics'
    await nextTick()
    expect(vm.nameExists).toBe(true)
    expect(logger.warn).toHaveBeenCalledWith('Scope name already exists', expect.anything())
    expect(snackbarState.color).toBe('warning')
    ;(vm.scopeData as { name: string }).name = 'x'
    await nextTick()
    expect(vm.nameExists).toBe(false)
  })

  it('requires a methodology and offers the loaded workflow pairs', async () => {
    const { wrapper } = await mountView()
    const select = wrapper
      .findAllComponents({ name: 'VSelect' })
      .find(c => c.props('label') === 'Methodology')

    expect(select?.props('items')).toEqual([
      expect.objectContaining({ id: 'wp-1', displayName: 'ClinGen (11)' })
    ])
    const rule = (select?.props('rules') as Array<(v: unknown) => unknown>)[0]
    expect(rule?.(null)).toBe('Choose a methodology')
    expect(rule?.('wp-1')).toBe(true)
  })

  it('does not submit an invalid form', async () => {
    const { store, vm } = await mountView()
    const create = vi.spyOn(store, 'createScope').mockResolvedValue({ id: 's9' } as never)
    vm.valid = false
    await call(vm, 'handleSubmit')
    expect(create).not.toHaveBeenCalled()
  })

  it('creates the scope with only API fields, invites members and opens the dashboard', async () => {
    const { store, vm } = await mountView()
    vi.useFakeTimers()
    const create = vi
      .spyOn(store, 'createScope')
      .mockResolvedValue({ id: 's9', name: 'n' } as never)
    const invite = vi
      .spyOn(store, 'inviteMember')
      .mockResolvedValueOnce(undefined as never)
      .mockRejectedValueOnce(new Error('already member'))
    vm.valid = true
    vm.scopeData = {
      name: 'kidney-genetics',
      display_name: 'Kidney Genetics',
      description: '',
      institution: '',
      is_public: true,
      default_workflow_pair_id: 'wp-1'
    }
    vm.pendingMembers = [
      { user: { id: 'u1' }, role: 'curator' },
      { user: { id: 'u2' }, role: 'viewer' }
    ]
    await call(vm, 'handleSubmit')
    expect(create).toHaveBeenCalledWith({
      name: 'kidney-genetics',
      display_name: 'Kidney Genetics',
      description: '',
      institution: '',
      is_public: true,
      default_workflow_pair_id: 'wp-1'
    })
    expect(invite).toHaveBeenCalledTimes(2)
    expect(invite).toHaveBeenCalledWith('s9', { user_id: 'u1', role: 'curator' })
    expect(logger.warn).toHaveBeenCalledWith(
      'Failed to invite member',
      expect.objectContaining({ user_id: 'u2' })
    )
    expect(snackbarState.message).toBe('Scope created successfully!')
    vi.advanceTimersByTime(1000)
    expect(routerPush).toHaveBeenCalledWith({
      name: 'scope-dashboard',
      params: { scopeId: 's9' }
    })
  })

  it('shows the API error detail when creation fails', async () => {
    const { store, vm } = await mountView()
    vi.spyOn(store, 'createScope').mockRejectedValue({
      message: 'Request failed',
      response: { data: { detail: 'Scope exists' } }
    })
    vm.valid = true
    ;(vm.scopeData as { default_workflow_pair_id: string }).default_workflow_pair_id = 'wp-1'
    await call(vm, 'handleSubmit')
    expect(snackbarState.message).toBe('Failed to create scope: Scope exists')
    expect(snackbarState.color).toBe('error')
    expect(vm.loading).toBe(false)
  })

  it('goes back on cancel and validates the name on blur', async () => {
    const { vm } = await mountView()
    call(vm, 'cancel')
    expect(routerBack).toHaveBeenCalled()
    call(vm, 'validateName')
  })

  it('searches users with a debounce and hides already added members', async () => {
    const { vm } = await mountView()
    vi.useFakeTimers()
    vi.mocked(usersApi.searchUsers).mockResolvedValue([
      { id: 'u1', name: 'Ada', email: 'ada@x.org' },
      { id: 'u2', name: null, email: 'bob@x.org' }
    ] as never)
    vm.pendingMembers = [{ user: { id: 'u1' }, role: 'curator' }]
    const search = vm.onUserSearch as (q: string) => void
    search('a')
    expect(vm.userSearchResults).toEqual([])
    search('ad')
    search('ada')
    await vi.advanceTimersByTimeAsync(300)
    expect(usersApi.searchUsers).toHaveBeenCalledTimes(1)
    expect(vm.userSearchResults).toEqual([
      { id: 'u2', name: null, email: 'bob@x.org', displayName: 'bob@x.org' }
    ])
  })

  it('clears the results and logs when the user search fails', async () => {
    const { vm } = await mountView()
    vi.useFakeTimers()
    vi.mocked(usersApi.searchUsers).mockRejectedValue(new Error('boom'))
    call(vm, 'onUserSearch', 'ada')
    await vi.advanceTimersByTimeAsync(300)
    expect(vm.userSearchResults).toEqual([])
    expect(logger.error).toHaveBeenCalledWith(
      'User search failed',
      expect.objectContaining({ error: 'boom' })
    )
  })

  it('adds and removes pending members and resets the dialog', async () => {
    const { vm } = await mountView()
    call(vm, 'addPendingMember')
    expect(vm.pendingMembers).toEqual([])
    vm.showAddMemberDialog = true
    vm.selectedMember = { id: 'u1', name: 'Ada', email: 'a@x.org' }
    vm.memberRole = 'reviewer'
    call(vm, 'addPendingMember')
    expect(vm.pendingMembers).toEqual([
      { user: { id: 'u1', name: 'Ada', email: 'a@x.org' }, role: 'reviewer' }
    ])
    expect(vm.showAddMemberDialog).toBe(false)
    expect(vm.selectedMember).toBeNull()
    expect(vm.memberRole).toBe('curator')
    call(vm, 'removePendingMember', 'u1')
    expect(vm.pendingMembers).toEqual([])
  })
})

describe('ScopeDashboard', () => {
  const scope = {
    id: 's1',
    name: 'kidney',
    display_name: 'Kidney Genetics',
    description: 'Renal genes',
    is_public: true,
    is_active: true
  }

  const mountView = async (role: 'admin' | 'viewer' | null = 'admin', tab = 'genes') => {
    routeState.params = { scopeId: 's1', tab }
    const store = useScopesStore()
    const fetchScope = vi.spyOn(store, 'fetchScope').mockImplementation(async () => {
      store.currentScope = scope as never
      return scope as never
    })
    const fetchUserRole = vi.spyOn(store, 'fetchUserRole').mockImplementation(async () => {
      store.currentUserRole = role
      return role
    })
    const fetchStatistics = vi.spyOn(store, 'fetchStatistics').mockResolvedValue({
      total_genes_assigned: 10,
      active_curations: 5,
      draft_curations: 2,
      submitted_curations: 1,
      curations_in_review: 3,
      total_curations: 9,
      member_count: 4
    } as never)
    const wrapper = mount(ScopeDashboard, opts())
    await flushPromises()
    return { wrapper, store, fetchScope, fetchUserRole, fetchStatistics, vm: vmOf(wrapper) }
  }

  it('loads the scope, the role and the statistics and shows the header', async () => {
    const { wrapper, fetchScope, fetchUserRole, fetchStatistics } = await mountView()
    expect(fetchScope).toHaveBeenCalledWith('s1')
    expect(fetchUserRole).toHaveBeenCalledWith('s1')
    expect(fetchStatistics).toHaveBeenCalledWith('s1')
    expect(wrapper.text()).toContain('Kidney Genetics')
    expect(wrapper.text()).toContain('Renal genes')
    expect(routerReplace).not.toHaveBeenCalled()
  })

  it('shows the real scope role with a platform-admin suffix in the chip', async () => {
    const { wrapper, store } = await mountView()
    store.membershipRole = 'curator'
    useAuthStore().user = { id: 'me', role: 'admin' } as never
    await nextTick()
    expect(wrapper.find('.v-chip').text()).toBe('curator (platform admin)')
  })

  it('shows em dashes, not zeros, until the statistics arrive', async () => {
    routeState.params = { scopeId: 's1', tab: 'overview' }
    const store = useScopesStore()
    vi.spyOn(store, 'fetchScope').mockImplementation(async () => {
      store.currentScope = scope as never
      return scope as never
    })
    vi.spyOn(store, 'fetchUserRole').mockResolvedValue('admin' as never)
    let release!: (v: never) => void
    vi.spyOn(store, 'fetchStatistics').mockReturnValue(new Promise(r => (release = r as never)))
    const wrapper = mount(ScopeDashboard, opts())
    await flushPromises()
    const tiles = wrapper
      .findAll('.text-headline-large')
      .map(t => t.text())
      .slice(1)
    expect(tiles).toEqual(['—', '—', '—', '—'])
    release({ total_genes_assigned: 10, member_count: 4 } as never)
    await flushPromises()
    expect(wrapper.findAll('.text-headline-large')[1]?.text()).toBe('10')
  })

  it('derives the in-progress count and curation progress from the statistics', async () => {
    const { vm } = await mountView()
    expect(vm.inProgressCount).toBe(6)
    expect(vm.curationProgress).toBe(50)
  })

  it('redirects to the overview tab when no tab is in the route', async () => {
    routeState.params = { scopeId: 's1' }
    const store = useScopesStore()
    vi.spyOn(store, 'fetchScope').mockResolvedValue(scope as never)
    vi.spyOn(store, 'fetchUserRole').mockResolvedValue('viewer' as never)
    vi.spyOn(store, 'fetchStatistics').mockResolvedValue(null as never)
    mount(ScopeDashboard, opts())
    await flushPromises()
    expect(routerReplace).toHaveBeenCalledWith({
      name: 'scope-dashboard',
      params: { scopeId: 's1', tab: 'overview' }
    })
  })

  it('falls back to the overview tab for an unknown tab and routes tab changes', async () => {
    const { vm } = await mountView('admin', 'bogus')
    expect(vm.activeTab).toBe('overview')
    vm.activeTab = 'curations'
    expect(routerPush).toHaveBeenCalledWith({
      name: 'scope-dashboard',
      params: { scopeId: 's1', tab: 'curations' }
    })
  })

  it('shows pending invitations next to the member count', async () => {
    const { store, vm, wrapper } = await mountView()
    vi.spyOn(store, 'fetchStatistics').mockResolvedValue({
      member_count: 2,
      pending_invitations: 1
    } as never)
    await call(vm, 'fetchScopeData')
    await flushPromises()

    expect(wrapper.text()).toContain('1 invited')
  })

  it('never shows more completed genes than total genes', async () => {
    const { store, vm } = await mountView()
    vi.spyOn(store, 'fetchStatistics').mockResolvedValue({
      total_genes_assigned: 1,
      active_curations: 3
    } as never)
    await call(vm, 'fetchScopeData')

    expect(vm.completedGenes).toBe(1)
    expect(vm.curationProgress).toBe(100)
  })

  it('refetches the statistics when the gene list reports a change', async () => {
    const { wrapper, fetchStatistics } = await mountView('admin', 'genes')
    fetchStatistics.mockClear()

    wrapper.findComponent({ name: 'GeneList' }).vm.$emit('changed')
    await flushPromises()

    expect(fetchStatistics).toHaveBeenCalledWith('s1')
  })

  it('keeps a deep-linked members tab while the role is still loading', async () => {
    routeState.params = { scopeId: 's1', tab: 'members' }
    const store = useScopesStore()
    vi.spyOn(store, 'fetchScope').mockImplementation(async () => {
      store.currentScope = scope as never
      return scope as never
    })
    vi.spyOn(store, 'fetchUserRole').mockImplementation(async () => {
      await new Promise(resolve => setTimeout(resolve, 20))
      store.currentUserRole = 'admin'
      return 'admin'
    })
    vi.spyOn(store, 'fetchStatistics').mockResolvedValue(null as never)
    const wrapper = mount(ScopeDashboard, opts())
    await new Promise(resolve => setTimeout(resolve, 50))
    await flushPromises()
    expect(routerPush).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Members')
  })

  it('treats missing statistics as zero progress', async () => {
    const { store, vm } = await mountView()
    vi.spyOn(store, 'fetchStatistics').mockResolvedValue(null as never)
    await call(vm, 'fetchScopeData')
    expect(vm.inProgressCount).toBe(0)
    expect(vm.curationProgress).toBe(0)
  })

  it('logs a failed load without throwing', async () => {
    routeState.params = { scopeId: 's1', tab: 'overview' }
    vi.spyOn(useScopesStore(), 'fetchScope').mockRejectedValue(new Error('403'))
    mount(ScopeDashboard, opts())
    await flushPromises()
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to fetch scope dashboard data',
      expect.objectContaining({ error: '403' })
    )
  })

  it('returns to the scope list after the scope is deleted', async () => {
    const { vm } = await mountView()
    call(vm, 'handleScopeDeleted')
    expect(routerPush).toHaveBeenCalledWith({ name: 'scopes' })
  })

  it('shows the store error instead of the dashboard', async () => {
    routeState.params = { scopeId: 's1', tab: 'overview' }
    const store = useScopesStore()
    vi.spyOn(store, 'fetchScope').mockImplementation(async () => {
      store.error = 'Scope not found'
      return undefined as never
    })
    vi.spyOn(store, 'fetchUserRole').mockResolvedValue(null as never)
    vi.spyOn(store, 'fetchStatistics').mockResolvedValue(null as never)
    const wrapper = mount(ScopeDashboard, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Scope not found')
  })
})
