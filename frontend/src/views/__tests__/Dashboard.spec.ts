import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import Dashboard from '@/views/Dashboard.vue'

const mountView = () =>
  mount(Dashboard, {
    global: { stubs: { RouterLink: true, PendingInvitations: true } }
  })

describe('Dashboard view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue(undefined as never)
  })

  it('counts active scopes from the scopes store', async () => {
    useScopesStore().scopes = [
      { id: 'a', is_active: true },
      { id: 'b', is_active: false }
    ] as never
    const wrapper = mountView()
    await flushPromises()
    expect(useScopesStore().fetchUserScopes).toHaveBeenCalled()
    expect(
      (wrapper.vm as unknown as { stats: { active_scopes: number } }).stats.active_scopes
    ).toBe(1)
  })

  it('greets the signed-in user', () => {
    const auth = useAuthStore()
    auth.user = { full_name: 'Ada Lovelace', role: 'user' } as never
    const wrapper = mountView()
    expect(wrapper.text()).toContain('Welcome back, Ada Lovelace')
  })

  it('falls back to User when there is no user', () => {
    const wrapper = mountView()
    expect(wrapper.text()).toContain('Welcome back, User')
  })

  it('shows a spinner while dashboard data loads', async () => {
    const auth = useAuthStore()
    auth.fetchDashboardStats = vi.fn(() => new Promise(() => {})) as never
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
  })

  it('shows the empty activity state and no admin link for a normal user', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('No recent activity')
    expect(wrapper.text()).not.toContain('Schema Management')
  })

  it('shows the admin-only schema link for admins', async () => {
    const auth = useAuthStore()
    auth.user = { full_name: 'Root', role: 'admin' } as never
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Schema Management')
  })

  it('still renders with zeroed stats when loading fails', async () => {
    const auth = useAuthStore()
    auth.fetchDashboardStats = vi.fn().mockRejectedValue(new Error('boom')) as never
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.v-progress-circular').exists()).toBe(false)
    expect(wrapper.text()).toContain('No recent activity')
  })
})
