import { describe, it, expect, vi, beforeEach } from 'vitest'

const auth = vi.hoisted(() => ({
  isAuthenticated: true,
  user: { role: 'curator' } as { role: string } | null,
  roles: ['curator'] as string[],
  hasRole: (role: string): boolean => auth.roles.includes(role),
  hasAnyRole: (roles: string[]): boolean => roles.some(r => auth.roles.includes(r))
}))

const nav = vi.hoisted(() => ({
  routes: [] as Array<{ name: string; path: string; meta: Record<string, unknown> }>,
  current: { name: 'Home', matched: [] as Array<{ name: string; meta: Record<string, unknown> }> }
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => auth
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    getRoutes: () => nav.routes,
    hasRoute: (name: string) => nav.routes.some(r => r.name === name),
    resolve: (to: { name: string }) => ({
      name: to.name,
      meta: nav.routes.find(r => r.name === to.name)?.meta ?? {}
    })
  }),
  useRoute: () => nav.current
}))

import { useNavigation } from '../useNavigation'

const route = (name: string, meta: Record<string, unknown> = {}) => ({
  name,
  path: `/${name.toLowerCase()}`,
  meta
})

describe('useNavigation', () => {
  beforeEach(() => {
    auth.isAuthenticated = true
    auth.user = { role: 'curator' }
    auth.roles = ['curator']
    nav.current = { name: 'Home', matched: [] }
    nav.routes = [
      route('Home', { showInMainMenu: true, menuOrder: 2, icon: 'mdi-home', title: 'Home' }),
      route('Scopes', { showInMainMenu: true, menuOrder: 1, menuLabel: 'Scopes' }),
      route('Admin', { showInMainMenu: true, requiredRoles: ['admin'] }),
      route('Login', { showInMainMenu: true, requiresGuest: true }),
      route('Profile', { showInUserMenu: true, requiresAuth: true, title: 'Profile' }),
      route('Landing', { isDefaultLandingPage: true }),
      route('UserManagement'),
      route('GeneAdmin'),
      route('SchemaManagement'),
      route('GeneAssignments'),
      route('ScopeSelection'),
      route('Precurations'),
      route('Curations'),
      route('ValidationDashboard'),
      route('About'),
      route('FAQ')
    ]
  })

  describe('hasAccess', () => {
    it('enforces authentication, guest-only and role requirements', () => {
      const { hasAccess } = useNavigation()

      expect(hasAccess({})).toBe(true)
      expect(hasAccess({ requiresAuth: true })).toBe(true)

      auth.isAuthenticated = false
      expect(hasAccess({ requiresAuth: true })).toBe(false)
      expect(hasAccess({ requiresGuest: true })).toBe(true)

      auth.isAuthenticated = true
      expect(hasAccess({ requiresGuest: true })).toBe(false)
      expect(hasAccess({ requiredRoles: ['admin'] })).toBe(false)
      expect(hasAccess({ requiredRoles: ['admin', 'curator'] })).toBe(true)
      expect(hasAccess({ requiredRoles: [] })).toBe(true)
    })
  })

  describe('mainMenuItems', () => {
    it('lists accessible main-menu routes sorted by menuOrder', () => {
      const { mainMenuItems } = useNavigation()

      expect(mainMenuItems.value.map(i => i.name)).toEqual(['Scopes', 'Home'])
    })

    it('derives title, icon, defaults and aria label from route meta', () => {
      const { mainMenuItems } = useNavigation()
      const [scopes, home] = mainMenuItems.value

      expect(scopes).toMatchObject({
        title: 'Scopes',
        badgeColor: 'error',
        dividerBefore: false,
        dividerAfter: false,
        order: 1,
        children: []
      })
      expect(scopes?.ariaLabel).toBe('Scopes')
      expect(scopes?.to).toEqual({ name: 'Scopes' })
      expect(home).toMatchObject({ title: 'Home', icon: 'mdi-home', order: 2 })
    })

    it('shows admin-only routes to admins', () => {
      auth.roles = ['admin']
      const { mainMenuItems } = useNavigation()

      expect(mainMenuItems.value.map(i => i.name)).toContain('Admin')
    })

    it('shows guest-only routes only to guests', () => {
      auth.isAuthenticated = false
      const { mainMenuItems } = useNavigation()

      expect(mainMenuItems.value.map(i => i.name)).toContain('Login')
      expect(mainMenuItems.value.map(i => i.name)).not.toContain('Admin')
    })
  })

  describe('userMenuItems', () => {
    it('lists user-menu routes only when authenticated', () => {
      const { userMenuItems } = useNavigation()
      expect(userMenuItems.value.map(i => i.name)).toEqual(['Profile'])

      auth.isAuthenticated = false
      expect(useNavigation().userMenuItems.value).toEqual([])
    })
  })

  describe('static submenus', () => {
    it('curationMenuItems is empty without curation access', () => {
      auth.roles = ['viewer']
      const { curationMenuItems } = useNavigation()

      expect(curationMenuItems.value).toEqual([])
    })

    it('curationMenuItems keeps only links whose routes exist, sorted by order', () => {
      nav.routes = nav.routes.filter(r => r.name !== 'Precurations')
      const { curationMenuItems } = useNavigation()

      expect(curationMenuItems.value.map(i => i.name)).toEqual([
        'assignments',
        'new-assignment',
        'curations',
        'validation'
      ])
    })

    it('helpMenuItems lists Documentation, FAQ and About when routes exist', () => {
      const { helpMenuItems } = useNavigation()

      expect(helpMenuItems.value.map(i => i.name)).toEqual(['documentation', 'faq', 'about'])
    })

    it('adminMenuItems requires admin role and existing routes', () => {
      const { adminMenuItems } = useNavigation()
      expect(adminMenuItems.value).toEqual([])

      auth.roles = ['admin']
      expect(useNavigation().adminMenuItems.value.map(i => i.name)).toEqual([
        'user-management',
        'gene-management',
        'schema-management'
      ])
    })
  })

  describe('active route helpers', () => {
    it('isActive compares against the current route name', () => {
      const { isActive } = useNavigation()

      expect(isActive('Home')).toBe(true)
      expect(isActive('Scopes')).toBe(false)
    })

    it('hasActiveChild checks children names against the current route', () => {
      const { hasActiveChild } = useNavigation()

      expect(hasActiveChild([{ name: 'Scopes' }, { name: 'Home' }])).toBe(true)
      expect(hasActiveChild([{ name: 'Scopes' }])).toBe(false)
      expect(hasActiveChild([])).toBe(false)
      expect(hasActiveChild(undefined)).toBe(false)
    })
  })

  describe('breadcrumbs', () => {
    it('starts with Home and marks the last matched route as disabled', () => {
      nav.current = {
        name: 'Curations',
        matched: [
          { name: 'Curations', meta: { breadcrumb: 'Curations' } },
          { name: 'CurationDetail', meta: { title: 'Detail' } }
        ]
      }
      const { breadcrumbs } = useNavigation()

      expect(breadcrumbs.value).toEqual([
        { name: 'Home', to: { name: 'Home' }, disabled: false },
        { name: 'Curations', to: { name: 'Curations' }, disabled: false },
        { name: 'Detail', to: { name: 'CurationDetail' }, disabled: true }
      ])
    })

    it('skips routes that hide their breadcrumb', () => {
      nav.current = {
        name: 'Hidden',
        matched: [{ name: 'Hidden', meta: { hideBreadcrumb: true } }]
      }
      const { breadcrumbs } = useNavigation()

      expect(breadcrumbs.value.map(c => c.name)).toEqual(['Home'])
    })
  })

  describe('defaultLandingPage', () => {
    it('uses the route flagged as default landing page', () => {
      const { defaultLandingPage } = useNavigation()

      expect(defaultLandingPage.value).toEqual({ name: 'Landing' })
    })

    it('falls back to Dashboard when no route is flagged', () => {
      nav.routes = nav.routes.filter(r => r.name !== 'Landing')
      const { defaultLandingPage } = useNavigation()

      expect(defaultLandingPage.value).toEqual({ name: 'Dashboard' })
    })
  })

  it('routeToMenuItem applies defaults for routes without meta', () => {
    const { routeToMenuItem } = useNavigation()

    const item = routeToMenuItem({
      name: 'Bare',
      path: '/bare',
      meta: undefined
    } as unknown as Parameters<typeof routeToMenuItem>[0])

    expect(item).toMatchObject({ name: 'Bare', title: 'Bare', order: 999, ariaLabel: 'Bare' })
  })
})
