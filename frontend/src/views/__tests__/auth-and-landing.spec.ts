/**
 * Behaviour tests for the static pages and the auth/landing views:
 * NotFound, NotAuthorized, Login, Register, Home.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import NotFound from '@/views/NotFound.vue'
import NotAuthorized from '@/views/NotAuthorized.vue'
import router from '@/router'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Home from '@/views/Home.vue'
import { useAuthStore } from '@/stores/auth'

const { routerPush, routeState, logger, showError, showSuccess } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routeState: {
    params: {} as Record<string, string>,
    query: {} as Record<string, string>,
    fullPath: '/'
  },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  showError: vi.fn(),
  showSuccess: vi.fn()
}))

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: routerPush, back: vi.fn() }),
  useRoute: () => routeState
}))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/composables/useNotifications', () => ({
  showError,
  showSuccess,
  showInfo: vi.fn(),
  showWarning: vi.fn()
}))

const mountOpts = (pinia: ReturnType<typeof createPinia>) => ({
  global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
})

describe('static pages', () => {
  it('NotFound shows the requested path and a Home action', () => {
    routeState.fullPath = '/no/such/page?x=1'
    const wrapper = mount(NotFound, mountOpts(createPinia()))
    expect(wrapper.text()).toContain('Page Not Found')
    expect(wrapper.text()).toContain('/no/such/page?x=1')
    expect(wrapper.text()).toContain('Go home')
    expect(wrapper.text()).toContain('Gene catalogue')
    expect(wrapper.find('.text-error').exists()).toBe(false)
  })

  it('NotAuthorized offers Sign in to anonymous users', () => {
    routeState.query = { redirect: '/admin/users' }
    const wrapper = mount(NotAuthorized, mountOpts(createPinia()))
    expect(wrapper.text()).toContain('Access Denied')
    expect(wrapper.text()).toContain('administrator')
    const signIn = wrapper.findAllComponents({ name: 'VBtn' }).find(b => b.text() === 'Sign in')
    expect(signIn?.props('to')).toEqual({ name: 'Login', query: { redirect: '/admin/users' } })
  })

  it('NotAuthorized sends signed-in users to the dashboard', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    useAuthStore().isAuthenticated = true
    const wrapper = mount(NotAuthorized, mountOpts(pinia))
    expect(wrapper.text()).toContain('Go to dashboard')
    expect(wrapper.text()).not.toContain('Sign in')
  })

  it.each([
    ['NotFound', NotFound],
    ['NotAuthorized', NotAuthorized]
  ])('%s only links to routes that exist', (_name, page) => {
    const wrapper = mount(page, mountOpts(createPinia()))
    const named = wrapper
      .findAllComponents({ name: 'VBtn' })
      .map(btn => btn.props('to') as { name?: string } | string | undefined)
      .filter((to): to is { name: string } => typeof to === 'object' && !!to?.name)
    expect(named.length).toBeGreaterThan(0)
    for (const to of named) expect(router.hasRoute(to.name)).toBe(true)
  })
})

describe('Login', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    vi.clearAllMocks()
    routeState.query = {}
    pinia = createPinia()
    setActivePinia(pinia)
  })

  it('logs in with the entered credentials and redirects to Home', async () => {
    const auth = useAuthStore()
    const login = vi.spyOn(auth, 'login').mockResolvedValue(undefined as never)
    const wrapper = mount(Login, mountOpts(pinia))

    await wrapper.find('input[type="email"]').setValue('user@example.org')
    await wrapper.find('input[type="password"]').setValue('secret123')
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(login).toHaveBeenCalledWith({ email: 'user@example.org', password: 'secret123' })
    expect(showSuccess).not.toHaveBeenCalled()
    expect(routerPush).toHaveBeenCalledWith({ name: 'Home' })
  })

  it('validates only on blur or submit, not while typing', async () => {
    const wrapper = mount(Login, mountOpts(pinia))
    await wrapper.find('input[type="email"]').setValue('a')
    await wrapper.find('input[type="email"]').setValue('')
    await flushPromises()
    expect(wrapper.text()).not.toContain('Email is required')

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Email is required')
  })

  it('honours a redirect query parameter', async () => {
    routeState.query = { redirect: '/genes' }
    const auth = useAuthStore()
    vi.spyOn(auth, 'login').mockResolvedValue(undefined as never)
    const wrapper = mount(Login, mountOpts(pinia))

    await wrapper.find('input[type="email"]').setValue('user@example.org')
    await wrapper.find('input[type="password"]').setValue('secret123')
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(routerPush).toHaveBeenCalledWith('/genes')
  })

  it('ignores an off-site redirect query parameter', async () => {
    routeState.query = { redirect: '//evil.example' }
    const auth = useAuthStore()
    vi.spyOn(auth, 'login').mockResolvedValue(undefined as never)
    const wrapper = mount(Login, mountOpts(pinia))

    await wrapper.find('input[type="email"]').setValue('user@example.org')
    await wrapper.find('input[type="password"]').setValue('secret123')
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(routerPush).toHaveBeenLastCalledWith({ name: 'Home' })
  })

  it('shows exactly one error and lets the user retry with the right password', async () => {
    const auth = useAuthStore()
    const login = vi.spyOn(auth, 'login').mockImplementationOnce(async () => {
      auth.error = 'Incorrect email or password' as never
      throw {
        message: 'Request failed',
        response: { data: { detail: 'Incorrect email or password' } }
      }
    })
    const wrapper = mount(Login, mountOpts(pinia))

    await wrapper.find('input[type="email"]').setValue('user@example.org')
    await wrapper.find('input[type="password"]').setValue('wrong-pass')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(showError).not.toHaveBeenCalled()
    expect(logger.error).toHaveBeenCalled()
    expect(wrapper.text().match(/Incorrect email or password/g)).toHaveLength(1)
    expect(routerPush).not.toHaveBeenCalled()

    login.mockResolvedValueOnce(undefined as never)
    await wrapper.find('input[type="password"]').setValue('right-pass')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(login).toHaveBeenLastCalledWith({ email: 'user@example.org', password: 'right-pass' })
    expect(routerPush).toHaveBeenCalledWith({ name: 'Home' })
  })

  it('shows the required-field messages on an empty submit', async () => {
    const auth = useAuthStore()
    const login = vi.spyOn(auth, 'login')
    const wrapper = mount(Login, mountOpts(pinia))
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Email is required')
    expect(wrapper.text()).toContain('Password is required')
    expect(login).not.toHaveBeenCalled()
  })

  it('explains an expired session', async () => {
    routeState.query = { reason: 'expired' }
    const wrapper = mount(Login, mountOpts(pinia))
    expect(wrapper.text()).toContain('Your session expired. Sign in to continue.')
  })

  it('renders the auth store error as an alert', async () => {
    const auth = useAuthStore()
    auth.error = 'Account locked' as never
    const wrapper = mount(Login, mountOpts(pinia))
    await flushPromises()
    expect(wrapper.text()).toContain('Account locked')
    expect(wrapper.find('[role="alert"]').text()).toContain('Account locked')
  })

  it('offers invitation and public browse links and a research-use footer', () => {
    const wrapper = mount(Login, mountOpts(pinia))
    const targets = wrapper
      .findAllComponents(RouterLinkStub)
      .map(l => l.props('to') as { name?: string })
    expect(wrapper.find('h1').text()).toBe('Sign in to Gene Curator')
    expect(targets).toContainEqual({ name: 'Register' })
    expect(targets).toContainEqual({ name: 'GeneCatalogue' })
    expect(wrapper.text()).toContain('Ask your scope admin for an invitation')
    expect(wrapper.text()).toContain('Research use only')
    expect(wrapper.text()).not.toMatch(/forgot/i) // #374: no password-reset route, so no dead link
  })

  it('quick login fills the admin development credentials and submits', async () => {
    const auth = useAuthStore()
    const login = vi.spyOn(auth, 'login').mockResolvedValue(undefined as never)
    const wrapper = mount(Login, mountOpts(pinia))

    const adminButton = wrapper.findAll('button').find(b => b.text().includes('Admin'))
    expect(adminButton).toBeDefined()
    await adminButton!.trigger('click')
    await flushPromises()

    expect(login).toHaveBeenCalledWith({
      email: 'admin@genecurator.org',
      password: 'admin123'
    })
  })
})

describe('Register', () => {
  let pinia: ReturnType<typeof createPinia>
  beforeEach(() => {
    vi.clearAllMocks()
    pinia = createPinia()
    setActivePinia(pinia)
  })

  it('registers a valid account and navigates Home', async () => {
    const auth = useAuthStore()
    const register = vi.spyOn(auth, 'register').mockResolvedValue(undefined as never)
    const wrapper = mount(Register, mountOpts(pinia))

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('Ada Lovelace')
    await inputs[1]!.setValue('new@example.org')
    await inputs[2]!.setValue('Passw0rd')
    await inputs[3]!.setValue('Passw0rd')
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(register).toHaveBeenCalledWith({
      name: 'Ada Lovelace',
      email: 'new@example.org',
      password: 'Passw0rd',
      role: 'user',
      is_active: true,
      is_agent: false
    })
    expect(showSuccess).toHaveBeenCalledWith('Account created')
    expect(routerPush).toHaveBeenCalledWith({ name: 'Home' })
  })

  it('reports a failed registration without navigating', async () => {
    const auth = useAuthStore()
    vi.spyOn(auth, 'register').mockRejectedValue(new Error('Email taken'))
    const wrapper = mount(Register, mountOpts(pinia))

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('Dup User')
    await inputs[1]!.setValue('dup@example.org')
    await inputs[2]!.setValue('Passw0rd')
    await inputs[3]!.setValue('Passw0rd')
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(showError).toHaveBeenCalledWith('Registration failed. Please try again.')
    expect(routerPush).not.toHaveBeenCalled()
  })
})

describe('Register look', () => {
  it('is a flat bordered card like Login: no shadow, no gradient or blur', () => {
    const wrapper = mount(Register, mountOpts(createPinia()))
    const card = wrapper.find('.v-card')
    expect(card.classes()).toContain('v-card--variant-flat')
    expect(card.classes()).toContain('v-card--border')
    expect(card.classes().join(' ')).not.toMatch(/elevation/)
    expect(wrapper.find('h1').text()).toBe('Create account')
  })
})

describe('Register password rule', () => {
  it('rejects a 7 character password and never calls the API', async () => {
    setActivePinia(createPinia())
    const register = vi.spyOn(useAuthStore(), 'register')
    const wrapper = mount(Register, mountOpts(createPinia()))
    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('Ada')
    await inputs[1]!.setValue('a@example.org')
    await inputs[2]!.setValue('abcdefg')
    await inputs[3]!.setValue('abcdefg')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Password must be at least 8 characters')
    expect(register).not.toHaveBeenCalled()
  })
})

describe('Home', () => {
  let pinia: ReturnType<typeof createPinia>
  beforeEach(() => {
    vi.clearAllMocks()
    pinia = createPinia()
    setActivePinia(pinia)
  })

  it('is a quiet page: description and two actions, no tiles or feature grid', async () => {
    const wrapper = mount(Home, mountOpts(pinia))
    await flushPromises()

    expect(wrapper.text()).toContain('Methodology-agnostic platform')
    expect(wrapper.text()).toContain('Browse genes')
    expect(wrapper.text()).not.toContain('Key Features')
    expect(wrapper.text()).not.toContain('Curated Genes')
    expect(wrapper.findAll('.v-card')).toHaveLength(0)
  })

  it('shows Sign in to guests and no admin link to anyone', async () => {
    const wrapper = mount(Home, mountOpts(pinia))
    await flushPromises()

    expect(wrapper.text()).toContain('Sign in')
    expect(wrapper.text()).not.toContain('Manage Genes')
    expect(wrapper.text()).not.toContain('Recent Activity')
  })
})
