import { describe, it, expect, vi, beforeEach } from 'vitest'
import router from '../index'
import { useAuthStore } from '@/stores/auth'
import { logService } from '@/services/logService'

vi.mock('@/stores/auth', () => ({ useAuthStore: vi.fn() }))

vi.mock('@/services/logService', () => ({
  logService: { warn: vi.fn(), info: vi.fn(), debug: vi.fn(), error: vi.fn() }
}))

// Lazy route components: stub them so navigation can complete without rendering views
const stub = { default: { render: () => null } }
vi.mock('@/views/Home.vue', () => stub)
vi.mock('@/views/Login.vue', () => stub)
vi.mock('@/views/Register.vue', () => stub)
vi.mock('@/views/FAQ.vue', () => stub)
vi.mock('@/views/Dashboard.vue', () => stub)
vi.mock('@/views/NotAuthorized.vue', () => stub)
vi.mock('@/views/NotFound.vue', () => stub)
vi.mock('@/views/About.vue', () => stub)
vi.mock('@/views/UserManagement.vue', () => stub)
vi.mock('@/views/scope/ScopeList.vue', () => stub)

interface FakeAuth {
  isAuthenticated: boolean
  token: string | null
  initialize: ReturnType<typeof vi.fn>
  hasRole: ReturnType<typeof vi.fn>
}

function useFakeAuth(overrides: Partial<FakeAuth> = {}): FakeAuth {
  const auth: FakeAuth = {
    isAuthenticated: false,
    token: null,
    initialize: vi.fn().mockResolvedValue(undefined),
    hasRole: vi.fn().mockReturnValue(false),
    ...overrides
  }
  vi.mocked(useAuthStore).mockReturnValue(auth as never)
  return auth
}

describe('router guards', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    document.title = ''
    localStorage.clear()
    // Start every test from a known route (the guard needs an auth store to read)
    useFakeAuth()
    await router.push('/about')
  })

  it('sends anonymous users from protected routes to login with a redirect back', async () => {
    useFakeAuth()

    await router.push('/dashboard')

    expect(router.currentRoute.value.name).toBe('Login')
    expect(router.currentRoute.value.query).toEqual({ redirect: '/dashboard' })
  })

  it('sends signed-in users away from guest-only pages', async () => {
    useFakeAuth({ isAuthenticated: true })

    await router.push('/login')

    expect(router.currentRoute.value.name).toBe('Dashboard')
  })

  it('sends a signed-in user on /login to the same-origin redirect target', async () => {
    useFakeAuth({ isAuthenticated: true })

    await router.push('/login?redirect=/faq?x=1')

    expect(router.currentRoute.value.fullPath).toBe('/faq?x=1')
  })

  it.each(['//evil.example', 'https://evil.example', '/\\evil.example'])(
    'ignores the unsafe redirect %s',
    async target => {
      useFakeAuth({ isAuthenticated: true })

      await router.push({ name: 'Login', query: { redirect: target } })

      expect(router.currentRoute.value.name).toBe('Dashboard')
    }
  )

  it('sends signed-in users from the landing page to the dashboard', async () => {
    useFakeAuth({ isAuthenticated: true })

    await router.push('/')

    expect(router.currentRoute.value.name).toBe('Dashboard')
  })

  it('still shows the landing page to anonymous users', async () => {
    useFakeAuth()

    await router.push('/')

    expect(router.currentRoute.value.name).toBe('Home')
  })

  it('lists My Work and Review Queue as top-level menu items', () => {
    for (const name of ['GeneAssignments', 'review-queue']) {
      expect(router.getRoutes().find(r => r.name === name)?.meta).toMatchObject({
        showInMainMenu: true
      })
    }
  })

  it('lets anonymous users reach guest-only pages', async () => {
    useFakeAuth()

    await router.push('/register')

    expect(router.currentRoute.value.name).toBe('Register')
  })

  it('sends users without a required role to the not-authorized page', async () => {
    const auth = useFakeAuth({ isAuthenticated: true })
    auth.hasRole.mockReturnValue(false)

    await router.push('/admin/users')

    expect(auth.hasRole).toHaveBeenCalledWith('admin')
    expect(router.currentRoute.value.name).toBe('NotAuthorized')
  })

  it('admits users holding one of the required roles', async () => {
    const auth = useFakeAuth({ isAuthenticated: true })
    auth.hasRole.mockImplementation((role: string) => role === 'admin')

    await router.push('/admin/users')

    expect(router.currentRoute.value.name).toBe('UserManagement')
  })

  it('allows public pages without authentication and sets the document title', async () => {
    useFakeAuth()

    await router.push('/about')

    expect(router.currentRoute.value.name).toBe('About')
    expect(document.title).toBe('About | Gene Curator')
  })

  it('uses the bare application title when a route has no title', async () => {
    useFakeAuth()
    router.addRoute({ path: '/untitled-probe', name: 'UntitledProbe', component: stub.default })

    await router.push('/untitled-probe')

    expect(document.title).toBe('Gene Curator')
    router.removeRoute('UntitledProbe')
  })

  it('renders the not-found page for unknown paths', async () => {
    useFakeAuth()

    await router.push('/no/such/page')

    expect(router.currentRoute.value.name).toBe('NotFound')
  })

  it('initialises the auth store when a token exists but the user is not yet authenticated', async () => {
    const auth = useFakeAuth({ token: 'stored-token' })

    await router.push('/faq')

    expect(auth.initialize).toHaveBeenCalledTimes(1)
  })

  it('skips initialisation when there is no token or the user is already authenticated', async () => {
    const anonymous = useFakeAuth()
    await router.push('/faq')
    expect(anonymous.initialize).not.toHaveBeenCalled()

    const signedIn = useFakeAuth({ isAuthenticated: true, token: 'x' })
    await router.push('/faq')
    expect(signedIn.initialize).not.toHaveBeenCalled()
  })

  it('logs a warning but keeps navigating when auth initialisation fails', async () => {
    const auth = useFakeAuth({ token: 'stored-token' })
    auth.initialize.mockRejectedValue(new Error('token expired'))

    await router.push('/faq')

    expect(logService.warn).toHaveBeenCalledWith('Auth initialization failed', {
      error: 'token expired',
      stack: expect.any(String)
    })
    expect(router.currentRoute.value.name).toBe('FAQ')
  })

  it('restores the scroll position on back navigation and otherwise scrolls to the top', () => {
    const scrollBehavior = router.options.scrollBehavior
    const to = router.currentRoute.value
    const from = router.currentRoute.value

    expect(scrollBehavior?.(to, from, null)).toEqual({ top: 0 })
    expect(scrollBehavior?.(to, from, { left: 0, top: 240 })).toEqual({ left: 0, top: 240 })
  })
})
