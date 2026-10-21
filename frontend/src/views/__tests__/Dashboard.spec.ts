import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import Dashboard from '@/views/Dashboard.vue'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const mountView = () =>
  mount(Dashboard, {
    global: { stubs: { RouterLink: true, PendingInvitations: true } }
  })

describe('Dashboard view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue(undefined as never)
  })

  it('lists the real scopes from the scopes store', async () => {
    useScopesStore().scopes = [
      { id: 'a', name: 'kidney', display_name: 'Kidney', is_active: true },
      { id: 'b', name: 'heart', display_name: 'Heart', is_active: false }
    ] as never
    const wrapper = mountView()
    await flushPromises()
    expect(useScopesStore().fetchUserScopes).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Kidney')
    expect(wrapper.text()).toContain('Heart')
  })

  it('greets the signed-in user by name', () => {
    useAuthStore().user = { name: 'Ada Lovelace', role: 'user' } as never
    expect(mountView().text()).toContain('Welcome back, Ada Lovelace')
  })

  it('falls back to User when there is no user', () => {
    expect(mountView().text()).toContain('Welcome back, User')
  })

  it('shows a spinner while scopes load', async () => {
    vi.mocked(useScopesStore().fetchUserScopes).mockReturnValue(new Promise(() => {}) as never)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
  })

  it('shows the empty state and no admin link for a normal user', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('No scopes assigned')
    expect(wrapper.text()).not.toContain('Schema Management')
  })

  it('shows the admin-only schema link for admins', async () => {
    useAuthStore().user = { name: 'Root', role: 'admin' } as never
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Schema Management')
  })

  it('still renders when loading scopes fails', async () => {
    vi.mocked(useScopesStore().fetchUserScopes).mockRejectedValue(new Error('boom'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.v-progress-circular').exists()).toBe(false)
    expect(wrapper.text()).toContain('No scopes assigned')
  })

  it('sends New Curation actions to the scopes list, not the removed wizard', () => {
    const targets = mountView()
      .findAllComponents({ name: 'VBtn' })
      .map(b => b.props('to'))
    expect(targets).toContain('/scopes')
    expect(targets).not.toContain('/scope-selection')
  })
})
