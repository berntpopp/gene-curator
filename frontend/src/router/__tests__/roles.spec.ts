import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import router from '../index'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/services/logService', () => ({
  logService: { warn: vi.fn(), info: vi.fn(), debug: vi.fn(), error: vi.fn() }
}))

const stub = { default: { render: () => null } }
vi.mock('@/views/Home.vue', () => stub)
vi.mock('@/views/Login.vue', () => stub)
vi.mock('@/views/About.vue', () => stub)
vi.mock('@/views/NotAuthorized.vue', () => stub)
vi.mock('@/views/UserManagement.vue', () => stub)
vi.mock('@/views/GeneAssignments.vue', () => stub)
vi.mock('@/views/curation/ReviewQueueView.vue', () => stub)

// Real auth store: scope roles (curator, reviewer) are not application roles, so an
// application role of 'user' must reach every scope-gated page (the backend enforces scope rights).
describe('router with the real auth store', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    await router.push('/about')
  })

  function signIn(role: 'user' | 'admin') {
    const auth = useAuthStore()
    auth.isAuthenticated = true
    auth.user = { id: 'u1', role } as typeof auth.user
  }

  it.each(['/review-queue', '/assignments'])('lets a plain user open %s', async path => {
    signIn('user')
    await router.push(path)
    expect(router.currentRoute.value.path).toBe(path)
  })

  it('keeps admin pages away from plain users but open to admins', async () => {
    signIn('user')
    await router.push('/admin/users')
    expect(router.currentRoute.value.name).toBe('NotAuthorized')

    signIn('admin')
    await router.push('/admin/users')
    expect(router.currentRoute.value.name).toBe('UserManagement')
  })

  it('sends guests to login with a redirect', async () => {
    await router.push('/review-queue')
    expect(router.currentRoute.value.name).toBe('Login')
    expect(router.currentRoute.value.query).toEqual({ redirect: '/review-queue' })
  })
})
