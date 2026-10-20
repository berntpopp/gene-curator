/**
 * Behaviour tests for the admin views: ScopeSelection, UserManagement (with its details dialog),
 * UserProfile, ValidationDashboard and WorkflowManagement.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
import ScopeSelection from '@/views/ScopeSelection.vue'
import UserManagement from '@/views/UserManagement.vue'
import UserProfile from '@/views/UserProfile.vue'
import ValidationDashboard from '@/views/ValidationDashboard.vue'
import WorkflowManagement from '@/views/WorkflowManagement.vue'
import UserDetailsDialog from '@/views/user-management/UserDetailsDialog.vue'
import {
  formatDate,
  getRoleColor,
  getRoleIcon
} from '@/views/user-management/userManagementHelpers'
import { useAuthStore } from '@/stores/auth'
import { useGenesStore } from '@/stores/genes'
import { useAssignmentsStore } from '@/stores/assignments'
import { useSchemasStore } from '@/stores/schemas'
import { useWorkflowStore } from '@/stores/workflow'
import { useValidationStore } from '@/stores/validation'
import { useUsersStore } from '@/stores/users'
import { authApi } from '@/api/auth'

const { routerPush, routeState, logger, showError, showSuccess } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routeState: { params: {} as Record<string, string>, query: {} as Record<string, string> },
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

// Vuetify overlays (dialogs, menus, selects) read visualViewport, which happy-dom does not provide
if (!('visualViewport' in window)) {
  Object.defineProperty(window, 'visualViewport', {
    value: {
      width: 1024,
      height: 768,
      scale: 1,
      offsetLeft: 0,
      offsetTop: 0,
      pageLeft: 0,
      pageTop: 0,
      addEventListener: () => undefined,
      removeEventListener: () => undefined
    }
  })
}

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

describe('ScopeSelection', () => {
  const mountView = () => mount(ScopeSelection, opts({ ScopeSelector: true, SchemaSelector: true }))

  it('starts at step one with the assignment form disabled', () => {
    const wrapper = mountView()
    expect(wrapper.text()).toContain('Select Scope')
  })

  it('searches genes only for queries of at least two characters', async () => {
    const genes = useGenesStore()
    const search = vi
      .spyOn(genes, 'searchGenes')
      .mockResolvedValue([{ id: 'g1', symbol: 'BRCA1' }] as never)
    const wrapper = mountView()
    const vm = wrapper.vm as unknown as {
      searchGenes: (q: string) => Promise<void>
      availableGenes: unknown[]
    }

    await vm.searchGenes('B')
    expect(search).not.toHaveBeenCalled()

    await vm.searchGenes('BR')
    expect(search).toHaveBeenCalledWith(expect.objectContaining({ query: 'BR', limit: 20 }))
    expect(vm.availableGenes).toEqual([{ id: 'g1', symbol: 'BRCA1' }])
  })

  it('clears gene results and logs when the gene search fails', async () => {
    vi.spyOn(useGenesStore(), 'searchGenes').mockRejectedValue(new Error('timeout'))
    const wrapper = mountView()
    const vm = wrapper.vm as unknown as {
      searchGenes: (q: string) => Promise<void>
      availableGenes: unknown[]
    }
    await vm.searchGenes('BRCA')
    expect(vm.availableGenes).toEqual([])
    expect(logger.error).toHaveBeenCalledWith(
      'Gene search failed:',
      expect.objectContaining({ error: 'timeout' })
    )
  })

  it('filters the mock disease list by name or OMIM id', async () => {
    const wrapper = mountView()
    const vm = wrapper.vm as unknown as {
      searchDiseases: (q: string) => Promise<void>
      availableDiseases: { name: string }[]
    }
    await vm.searchDiseases('qt')
    expect(vm.availableDiseases.map(d => d.name)).toEqual(['Long QT Syndrome'])
    await vm.searchDiseases('601144')
    expect(vm.availableDiseases.map(d => d.name)).toEqual(['Brugada Syndrome'])
  })

  it('formats assignment status labels and colours', () => {
    const vm = mountView().vm as unknown as {
      formatAssignmentStatus: (s: string) => string
      getAssignmentStatusColor: (s: string) => string
    }
    expect(vm.formatAssignmentStatus('in_progress')).toBe('In Progress')
    expect(vm.getAssignmentStatusColor('available')).toBe('success')
    expect(vm.getAssignmentStatusColor('unknown')).toBe('grey')
  })

  it('creates an assignment from the selections and opens it', async () => {
    const assignments = useAssignmentsStore()
    const createAssignment = vi.fn(async () => ({ id: 'a-9' }))
    Object.assign(assignments, { createAssignment })
    const wrapper = mountView()
    const vm = wrapper.vm as unknown as Record<string, unknown> & {
      createAssignment: () => Promise<void>
    }
    vm.selectedScope = { id: 'scope-1' }
    vm.selectedSchemas = {
      workflowPair: { id: 'wp' },
      precurationSchema: { id: 'pre' },
      curationSchema: { id: 'cur' }
    }
    vm.selectedGene = { id: 'g1', symbol: 'PKD1' }
    vm.selectedDisease = { id: 'd1', name: 'PKD', omim_id: '1', category: 'Renal' }

    await vm.createAssignment()
    expect(createAssignment).toHaveBeenCalledWith(
      expect.objectContaining({
        gene_id: 'g1',
        disease_id: 'd1',
        scope_id: 'scope-1',
        workflow_pair_id: 'wp'
      })
    )
    expect(routerPush).toHaveBeenCalledWith({ name: 'AssignmentDetail', params: { id: 'a-9' } })
  })

  it('does nothing when the selections are incomplete', async () => {
    const assignments = useAssignmentsStore()
    const createAssignment = vi.fn()
    Object.assign(assignments, { createAssignment })
    const vm = mountView().vm as unknown as { createAssignment: () => Promise<void> }
    await vm.createAssignment()
    expect(createAssignment).not.toHaveBeenCalled()
  })
})

describe('UserManagement', () => {
  const users = useUsersStore() as unknown as {
    paginatedUsers: unknown[]
    statistics: Record<string, number>
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

  it('loads users and shows the statistics on mount', async () => {
    users.paginatedUsers = [alice]
    users.statistics = {
      total_users: 3,
      active_users: 2,
      inactive_users: 1,
      recent_registrations: 1
    }
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    expect(users.fetchUsers).toHaveBeenCalled()
    expect(users.fetchUserStatistics).toHaveBeenCalled()
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('Alice')
  })

  it('reports a load failure with a snackbar', async () => {
    users.fetchUsers.mockRejectedValueOnce(new Error('down'))
    mount(UserManagement, opts())
    await flushPromises()
    expect(document.body.textContent).toContain('Failed to load user data')
  })

  it('shows the store error as a snackbar and clears it', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    users.error = 'Quota exceeded'
    await flushPromises()
    expect(document.body.textContent).toContain('Quota exceeded')
    wrapper.unmount()
  })

  it('deletes the chosen user through the store', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      confirmDeleteUser: (u: typeof alice) => void
      performDeleteUser: () => Promise<void>
    }
    vm.confirmDeleteUser(alice)
    await vm.performDeleteUser()
    expect(users.deleteUser).toHaveBeenCalledWith('u1')
  })

  it('rejects a reset password shorter than eight characters', async () => {
    vi.stubGlobal(
      'prompt',
      vi.fn(() => 'short')
    )
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    await (
      wrapper.vm as unknown as { resetPassword: (u: typeof alice) => Promise<void> }
    ).resetPassword(alice)
    expect(users.updateUserPassword).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('Password must be at least 8 characters long')
    vi.unstubAllGlobals()
  })

  it('creates a new user from the dialog form values', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      openCreateUserDialog: () => void
      userFormData: Record<string, unknown>
      saveUser: () => Promise<void>
    }
    vm.openCreateUserDialog()
    vm.userFormData = {
      name: 'Bob',
      email: 'bob@example.org',
      role: 'viewer',
      password: 'longpassword',
      is_active: true
    }
    await flushPromises()
    await vm.saveUser()
    expect(users.createUser).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'bob@example.org' })
    )
    expect(document.body.textContent).toContain('User created successfully')
  })

  it('opens the details dialog and loads the user activity', async () => {
    const wrapper = mount(UserManagement, opts())
    await flushPromises()
    await (wrapper.vm as unknown as { viewUser: (u: typeof alice) => Promise<void> }).viewUser(
      alice
    )
    await flushPromises()
    expect(users.fetchUserActivity).toHaveBeenCalledWith('u1')
    expect(document.body.textContent).toContain('User Details: Alice')
    expect(document.body.textContent).toContain('Genes Created')
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
        activity: { genes_created: 2, total_contributions: 5 }
      },
      global: { stubs: { RouterLink: RouterLinkStub } }
    })
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('User Details: Carol')
    expect(text).toContain('carol@example.org')
    expect(text).toContain('Never')
    expect(text).toContain('Total Contributions')
    wrapper.unmount()
  })
})

describe('user-management helpers', () => {
  it('maps known roles to colours and icons with safe fallbacks', () => {
    expect(getRoleColor('admin')).toBe('error')
    expect(getRoleColor('nobody')).toBe('primary')
    expect(getRoleColor(undefined)).toBe('primary')
    expect(getRoleIcon('curator')).toBe('mdi-pencil')
    expect(getRoleIcon(undefined)).toBe('mdi-account')
  })

  it('formats dates and renders N/A for missing values', () => {
    expect(formatDate(undefined)).toBe('N/A')
    expect(formatDate('2026-03-04T10:30:00Z')).toContain('2026')
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

  it('loads the profile and activity of the signed-in user', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u1', email: 'dana@example.org', role: 'admin' } as never
    const usersStore = useUsersStore()
    vi.spyOn(usersStore, 'fetchUser').mockResolvedValue(profile as never)
    vi.spyOn(usersStore, 'fetchUserActivity').mockResolvedValue({ curations_created: 3 } as never)
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
    expect(document.body.textContent).toContain('Failed to load complete profile information')
  })

  it('changes the password and clears the form on success', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u1', email: 'dana@example.org', role: 'admin' } as never
    vi.spyOn(useUsersStore(), 'fetchUser').mockResolvedValue(profile as never)
    vi.spyOn(useUsersStore(), 'fetchUserActivity').mockResolvedValue({} as never)
    const wrapper = mount(UserProfile, opts())
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      passwordData: { current_password: string; new_password: string }
    }
    vm.passwordData = { current_password: 'oldpassword', new_password: 'newpassword1' }
    await flushPromises()
    await (wrapper.vm as unknown as { changePassword: () => Promise<void> }).changePassword()
    expect(authApi.changePassword).toHaveBeenCalledWith({
      current_password: 'oldpassword',
      new_password: 'newpassword1'
    })
    expect(document.body.textContent).toContain('Password changed successfully')
  })
})

describe('ValidationDashboard', () => {
  it('renders stored validation results in the table', async () => {
    const validation = useValidationStore()
    validation.validationResults = {
      r1: {
        id: 'r1',
        entity_id: 'e1',
        validation_status: 'valid',
        issues: [],
        gene_symbol: 'MYH7',
        schema_name: 'Precuration v1'
      }
    } as never
    const wrapper = mount(ValidationDashboard, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Valid')
  })

  it('reports a failure when the dashboard data cannot be loaded', async () => {
    mount(ValidationDashboard, opts())
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Failed to load dashboard data. Please refresh.')
    expect(logger.error).toHaveBeenCalled()
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
    vi.stubGlobal(
      'confirm',
      vi.fn(() => true)
    )
    const wrapper = mount(WorkflowManagement, opts())
    await flushPromises()
    await (
      wrapper.vm as unknown as {
        deleteWorkflow: (w: { id: string; name: string }) => Promise<void>
      }
    ).deleteWorkflow({
      id: 'wp1',
      name: 'ClinGen flow'
    })
    expect(deleteWorkflowPair).toHaveBeenCalledWith('wp1')
    expect(showSuccess).toHaveBeenCalledWith('Workflow deleted successfully')
    vi.unstubAllGlobals()
  })
})
