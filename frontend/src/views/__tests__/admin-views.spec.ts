/**
 * Behaviour tests for the admin views: UserManagement (with its details dialog),
 * UserProfile and WorkflowManagement.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { call, vmOf } from './vm'
import { reactive } from 'vue'
import UserManagement from '@/views/UserManagement.vue'
import UserProfile from '@/views/UserProfile.vue'
import WorkflowManagement from '@/views/WorkflowManagement.vue'
import UserDetailsDialog from '@/views/user-management/UserDetailsDialog.vue'
import { getRoleColor, getRoleIcon, initials } from '@/views/user-management/userManagementHelpers'
import { useAuthStore } from '@/stores/auth'
import { useSchemasStore } from '@/stores/schemas'
import { useWorkflowStore } from '@/stores/workflow'
import { useUsersStore } from '@/stores/users'
import { useScopesStore } from '@/stores/scopes'
import { authApi } from '@/api/auth'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

const { routerPush, routeState, logger, showError, showSuccess, showSnackbar } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routeState: { params: {} as Record<string, string>, query: {} as Record<string, string> },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showSnackbar: vi.fn()
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
  showSnackbar,
  showInfo: vi.fn(),
  showWarning: vi.fn()
}))
vi.mock('@/api/auth', () => ({ authApi: { changePassword: vi.fn() } }))

// The users store is replaced by a reactive fake so the table and statistics can be driven directly
vi.mock('@/stores/users', () => {
  const fake = reactive({
    paginatedUsers: [] as unknown[],
    statistics: {} as Record<string, number>,
    error: null as string | null,
    fetchUsers: vi.fn(async () => undefined),
    fetchUserStatistics: vi.fn(async () => undefined),
    searchUsers: vi.fn(async () => undefined),
    clearSearch: vi.fn(),
    clearError: vi.fn(),
    createUser: vi.fn(async () => undefined),
    updateUser: vi.fn(async () => undefined),
    deleteUser: vi.fn(async () => undefined),
    activateUser: vi.fn(async () => undefined),
    deactivateUser: vi.fn(async () => undefined),
    updateUserPassword: vi.fn(async () => undefined),
    fetchUser: vi.fn(async () => undefined),
    fetchUserActivity: vi.fn(async () => ({ genes_created: 4, total_contributions: 9 }))
  })
  return { useUsersStore: () => fake }
})

let pinia: ReturnType<typeof createPinia>
const opts = (extraStubs: Record<string, boolean> = {}) => ({
  attachTo: document.body,
  global: {
    plugins: [pinia],
    stubs: { RouterLink: RouterLinkStub, ...extraStubs }
  }
})

beforeEach(() => {
  vi.clearAllMocks()
  pinia = createPinia()
  setActivePinia(pinia)
})

describe('UserManagement', () => {
  const users = useUsersStore() as unknown as {
    paginatedUsers: unknown[]
    statistics: Record<string, number | Record<string, number>>
    error: string | null
    fetchUsers: ReturnType<typeof vi.fn>
    fetchUserStatistics: ReturnType<typeof vi.fn>
    fetchUserActivity: ReturnType<typeof vi.fn>
    deleteUser: ReturnType<typeof vi.fn>
    updateUserPassword: ReturnType<typeof vi.fn>
    createUser: ReturnType<typeof vi.fn>
  }
  const alice = {
    id: 'u1',
    name: 'Alice',
    email: 'alice@example.org',
    role: 'curator',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    last_login: null
  }

  it('uses singular nouns for a count of one', async () => {
    users.statistics = {
      total_users: 1,
      active_users: 1,
      inactive_users: 0,
      role_distribution: { admin: 1 }
    }
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    expect(wrapper.find('[data-test="user-summary"]').text()).toBe('1 user · 1 admin · 0 inactive')
  })

  it('loads users and shows the statistics on mount', async () => {
    users.paginatedUsers = [alice]
    users.statistics = {
      total_users: 3,
      active_users: 2,
      inactive_users: 1,
      role_distribution: { admin: 2 }
    }
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    expect(users.fetchUsers).toHaveBeenCalled()
    expect(users.fetchUserStatistics).toHaveBeenCalled()
    expect(wrapper.find('[data-test="user-summary"]').text()).toBe(
      '3 users · 2 admins · 1 inactive'
    )
    expect(wrapper.text()).toContain('Alice')
  })

  it('falls back to zeros when statistics are empty', async () => {
    users.paginatedUsers = []
    users.statistics = {}
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    expect(wrapper.find('[data-test="user-summary"]').text()).toBe(
      '0 users · 0 admins · 0 inactive'
    )
    wrapper.unmount()
  })

  it('disables destructive row actions and edit fields only for the own row', async () => {
    useAuthStore().user = { id: 'u1' } as never
    const inactive = { ...alice, id: 'u3', name: 'Dora', is_active: false }
    users.paginatedUsers = [alice, inactive]
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const actions = wrapper.findAll('button[aria-label="User actions"]')
    const items = async (i: number) => {
      await actions[i]!.trigger('click')
      await flushPromises()
      const lists = document.querySelectorAll('.v-overlay__content .v-list')
      return [...lists[lists.length - 1]!.querySelectorAll('.v-list-item')]
    }
    const own = await items(0)
    expect(own.find(e => e.textContent?.includes('Deactivate'))?.className).toContain('disabled')
    expect(own.find(e => e.textContent?.includes('Delete User'))?.className).toContain('disabled')
    const other = await items(1)
    expect(other.some(e => e.textContent?.includes('Activate'))).toBe(true)
    expect(other.find(e => e.textContent?.includes('Delete User'))?.className).not.toContain(
      'disabled'
    )

    const vm = vmOf(wrapper)
    call(vm, 'editUser', alice)
    await flushPromises()
    expect(document.querySelector('.v-select.v-input--disabled')).not.toBeNull()
    expect(document.querySelector('.v-switch.v-input--disabled')).not.toBeNull()
    wrapper.unmount()
  })

  it('reports a load failure with a snackbar', async () => {
    users.fetchUsers.mockRejectedValueOnce(new Error('down'))
    mount(UserManagement, opts())
    await flushPromises()
    expect(showSnackbar).toHaveBeenCalledWith('Failed to load user data', 'error')
  })

  it('shows the store error as a snackbar and clears it', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    users.error = 'Quota exceeded'
    await flushPromises()
    expect(showSnackbar).toHaveBeenCalledWith('Quota exceeded', 'error')
    wrapper.unmount()
  })

  it('deletes the chosen user through the store', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const vm = vmOf(wrapper)
    call(vm, 'confirmDeleteUser', alice)
    await call(vm, 'performDeleteUser')
    expect(users.deleteUser).toHaveBeenCalledWith('u1')
  })

  it('opens a masked reset dialog and sends the password only when both fields match', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const vm = vmOf(wrapper)
    call(vm, 'resetPassword', alice)
    await flushPromises()
    const inputs = document.querySelectorAll<HTMLInputElement>('input[type="password"]')
    expect(inputs).toHaveLength(2)
    expect(document.body.textContent).not.toContain('Password must be at least 8')

    const type = async (i: number, v: string) => {
      inputs[i]!.value = v
      inputs[i]!.dispatchEvent(new Event('input'))
      await flushPromises()
    }
    const reset = [...document.querySelectorAll('button')].find(b =>
      b.textContent?.includes('Reset')
    )!
    await type(0, 'longpassword')
    await type(1, 'different')
    reset.click()
    await flushPromises()
    expect(users.updateUserPassword).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('Passwords do not match')

    await type(0, 'x'.repeat(129))
    await type(1, 'x'.repeat(129))
    reset.click()
    await flushPromises()
    expect(users.updateUserPassword).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('at most 128')

    await type(0, 'longpassword')
    await type(1, 'longpassword')
    reset.click()
    await flushPromises()
    expect(users.updateUserPassword).toHaveBeenCalledWith('u1', 'longpassword')
    wrapper.unmount()
  })

  it('reports a failed password reset', async () => {
    users.updateUserPassword.mockRejectedValueOnce(new Error('x'))
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const vm = vmOf(wrapper)
    call(vm, 'resetPassword', alice)
    await call(vm, 'performResetPassword', 'longpassword')
    expect(showSnackbar).toHaveBeenCalledWith('Failed to update password', 'error')
    wrapper.unmount()
  })

  it('recognises the signed-in admin own row', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u1' } as never
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const vm = vmOf(wrapper)
    expect(call(vm, 'isSelf', alice)).toBe(true)
    expect(call(vm, 'isSelf', { ...alice, id: 'u2' })).toBe(false)
    wrapper.unmount()
  })

  it('creates a new user from the dialog form values', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const vm = vmOf(wrapper)
    call(vm, 'openCreateUserDialog')
    vm.userFormData = {
      name: 'Bob',
      email: 'bob@example.org',
      role: 'viewer',
      password: 'longpassword',
      is_active: true
    }
    await flushPromises()
    await call(vm, 'saveUser')
    expect(users.createUser).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'bob@example.org' })
    )
    expect(showSnackbar).toHaveBeenCalledWith('User created successfully', 'success')
  })

  it('opens the details dialog and loads the user activity', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    await call(vmOf(wrapper), 'viewUser', alice)
    await flushPromises()
    expect(users.fetchUserActivity).toHaveBeenCalledWith('u1')
    expect(document.body.textContent).toContain('User Details: Alice')
    expect(document.body.textContent).not.toContain('Genes Created')
  })
})

describe('UserDetailsDialog', () => {
  it('shows the user fields and activity summary, and "Never" for no last login', async () => {
    const wrapper = mount(UserDetailsDialog, {
      attachTo: document.body,
      props: {
        modelValue: true,
        'onUpdate:modelValue': () => undefined,
        user: {
          id: 'u1',
          name: 'Carol',
          email: 'carol@example.org',
          role: 'viewer',
          is_active: true,
          last_login: null
        },
        activity: { scope_count: 3 }
      },
      global: { stubs: { RouterLink: RouterLinkStub } }
    })
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('User Details: Carol')
    expect(text).toContain('carol@example.org')
    expect(text).toContain('Never')
    expect(text).toContain('Scopes')
    expect(text).not.toContain('Total Contributions')
    wrapper.unmount()
  })
})

describe('user-management helpers', () => {
  it('maps known roles to colours and icons with safe fallbacks', () => {
    expect(getRoleColor('admin')).toBe('primary')
    expect(initials('Alice Smith')).toBe('AS')
    expect(initials(undefined)).toBe('')
    expect(getRoleColor('nobody')).toBe('primary')
    expect(getRoleColor(undefined)).toBe('primary')
    expect(getRoleIcon('admin')).toBe('mdi-shield-crown')
    expect(getRoleIcon(undefined)).toBe('mdi-account')
  })
})

describe('UserProfile', () => {
  const profile = {
    id: 'u1',
    email: 'dana@example.org',
    name: 'Dana',
    role: 'admin',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z'
  }

  it('lists the scope roles from the scopes store, not the app role', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u1', email: 'dana@example.org', role: 'user' } as never
    vi.spyOn(useUsersStore(), 'fetchUser').mockResolvedValue({ ...profile, role: 'user' } as never)
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockImplementation(async () => {
      useScopesStore().scopes = [
        { id: 's1', name: 'kidney', display_name: 'Kidney Genetics', user_role: 'curator' },
        { id: 's2', name: 'other', display_name: 'Other Scope', user_role: null }
      ] as never
      return [] as never
    })
    const wrapper = mount(UserProfile, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Kidney Genetics')
    expect(wrapper.text()).toContain('Curator')
    expect(wrapper.text()).not.toContain('Other Scope') // admin sees it, but no membership
    expect(wrapper.text()).not.toMatch(/\buser\b/)
  })

  it('loads the profile of the signed-in user', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u1', email: 'dana@example.org', role: 'admin' } as never
    const usersStore = useUsersStore()
    vi.spyOn(usersStore, 'fetchUser').mockResolvedValue(profile as never)
    const wrapper = mount(UserProfile, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Dana')
    expect(usersStore.fetchUser).toHaveBeenCalledWith('u1')
  })

  it('falls back to auth data and warns when the profile cannot be loaded', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u1', email: 'dana@example.org', role: 'admin' } as never
    vi.spyOn(useUsersStore(), 'fetchUser').mockRejectedValue(new Error('nope'))
    const wrapper = mount(UserProfile, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('dana@example.org')
    expect(showError).toHaveBeenCalledWith('Failed to load complete profile information')
  })

  it('changes the password and clears the form on success', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u1', email: 'dana@example.org', role: 'admin' } as never
    vi.spyOn(useUsersStore(), 'fetchUser').mockResolvedValue(profile as never)
    const wrapper = mount(UserProfile, opts())
    await flushPromises()
    const vm = vmOf(wrapper)
    vm.passwordData = { current_password: 'oldpassword', new_password: 'newpassword1' }
    vm.confirmPassword = 'newpassword1'
    await flushPromises()
    await call(vm, 'changePassword')
    expect(authApi.changePassword).toHaveBeenCalledWith({
      current_password: 'oldpassword',
      new_password: 'newpassword1'
    })
    expect(showSuccess).toHaveBeenCalledWith('Password changed successfully')
  })
})

describe('WorkflowManagement', () => {
  it('shows the workflow pairs from the schemas store', async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    vi.spyOn(schemas, 'fetchWorkflowPairs').mockImplementation(async () => {
      schemas.workflowPairs = [
        { id: 'wp1', name: 'ClinGen flow', status: 'active', usage_count: 0 }
      ] as never
      return undefined as never
    })
    const workflow = useWorkflowStore()
    vi.spyOn(workflow, 'fetchWorkflowAnalytics').mockResolvedValue(null as never)
    vi.spyOn(workflow, 'fetchPeerReviewers').mockResolvedValue(null as never)
    const wrapper = mount(WorkflowManagement, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('ClinGen flow')
  })

  it('deletes a workflow only after confirmation', async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
    vi.spyOn(useWorkflowStore(), 'fetchWorkflowAnalytics').mockResolvedValue(null as never)
    vi.spyOn(useWorkflowStore(), 'fetchPeerReviewers').mockResolvedValue(null as never)
    const deleteWorkflowPair = vi
      .spyOn(schemas, 'deleteWorkflowPair')
      .mockResolvedValue(undefined as never)
    confirmMock.mockResolvedValue(true)
    const wrapper = mount(WorkflowManagement, opts())
    await flushPromises()
    await call(vmOf(wrapper), 'deleteWorkflow', { id: 'wp1', name: 'ClinGen flow' })
    expect(deleteWorkflowPair).toHaveBeenCalledWith('wp1')
    expect(showSuccess).toHaveBeenCalledWith('Workflow deleted successfully')
    vi.unstubAllGlobals()
  })
})
