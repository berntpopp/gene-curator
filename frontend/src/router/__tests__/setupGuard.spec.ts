/** MUI-06: Setup pages (templates, workflows) need app admin or scope admin, not just sign-in. */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import router from '../index'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'

vi.mock('@/stores/auth', () => ({ useAuthStore: vi.fn() }))
vi.mock('@/stores/scopes', () => ({ useScopesStore: vi.fn() }))
vi.mock('@/services/logService', () => ({
  logService: { warn: vi.fn(), info: vi.fn(), debug: vi.fn(), error: vi.fn() }
}))
const stub = { default: { render: () => null } }
vi.mock('@/views/About.vue', () => stub)
vi.mock('@/views/NotAuthorized.vue', () => stub)
vi.mock('@/views/SchemaManagement.vue', () => stub)
vi.mock('@/views/SchemaEditor.vue', () => stub)

function signIn(appAdmin: boolean, roles: string[]) {
  vi.mocked(useAuthStore).mockReturnValue({
    isAuthenticated: true,
    token: 't',
    hasRole: (r: string) => appAdmin || r === 'user'
  } as never)
  const scopes = { scopes: [] as { user_role: string }[], fetchUserScopes: vi.fn() }
  scopes.fetchUserScopes.mockImplementation(async () => {
    scopes.scopes = roles.map(user_role => ({ user_role }))
  })
  vi.mocked(useScopesStore).mockReturnValue(scopes as never)
}

describe('Setup route guard', () => {
  beforeEach(async () => {
    signIn(false, [])
    await router.push('/about')
  })

  it.each(['/admin/schemas', '/admin/schemas/s1/edit'])('refuses a curator on %s', async path => {
    signIn(false, ['curator', 'viewer'])
    await router.push(path)
    expect(router.currentRoute.value.name).toBe('NotAuthorized')
  })

  it('admits a scope admin', async () => {
    signIn(false, ['admin'])
    await router.push('/admin/schemas')
    expect(router.currentRoute.value.name).toBe('SchemaManagement')
  })

  it('admits a platform admin', async () => {
    signIn(true, [])
    await router.push('/admin/schemas/s1/edit')
    expect(router.currentRoute.value.name).toBe('SchemaEditor')
  })
})
