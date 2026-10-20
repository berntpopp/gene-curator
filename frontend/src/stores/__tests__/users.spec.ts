import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { User } from '@/stores/users'
import { setActivePinia, createPinia } from 'pinia'
import { useUsersStore } from '@/stores/users'
import { usersApi } from '@/api/users'

vi.mock('@/api/users', () => ({
  usersApi: {
    getUsers: vi.fn(),
    searchUsers: vi.fn(),
    getUserStatistics: vi.fn(),
    getUser: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    updateUserPassword: vi.fn(),
    activateUser: vi.fn(),
    deactivateUser: vi.fn(),
    deleteUser: vi.fn(),
    getUserActivity: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(usersApi)

const user = (id: string, extra: Record<string, unknown> = {}) =>
  ({
    id,
    email: `${id}@example.org`,
    name: id,
    role: 'user',
    is_active: true,
    ...extra
  }) as User

/** Axios-style error carrying an API detail message. */
const withDetail = (detail: string) =>
  Object.assign(new Error('request failed'), { response: { data: { detail } } })

describe('useUsersStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('computed', () => {
    it('shows search results while searching and computes paging', () => {
      const store = useUsersStore()
      store.users = [user('u1')]
      store.searchResults = [user('s1')]
      store.totalUsers = 25
      store.itemsPerPage = 10
      store.currentPage = 2

      expect(store.paginatedUsers.map(u => u.id)).toEqual(['u1'])
      store.searchQuery = 'x'
      expect(store.paginatedUsers.map(u => u.id)).toEqual(['s1'])
      expect(store.totalPages).toBe(3)
      expect(store.hasNextPage).toBe(true)
      expect(store.hasPreviousPage).toBe(true)
    })
  })

  describe('fetchUsers', () => {
    it('loads a page and estimates the total', async () => {
      const store = useUsersStore()
      api.getUsers.mockResolvedValue([user('u1'), user('u2')])

      const result = await store.fetchUsers(2, 2)

      expect(api.getUsers).toHaveBeenCalledWith({ skip: 2, limit: 2 })
      expect(result).toHaveLength(2)
      expect(store.users).toHaveLength(2)
      expect(store.currentPage).toBe(2)
      expect(store.itemsPerPage).toBe(2)
      // full page -> more may follow
      expect(store.totalUsers).toBe(5)
      expect(store.loading).toBe(false)
    })

    it('estimates the total from a short last page', async () => {
      const store = useUsersStore()
      api.getUsers.mockResolvedValue([user('u1')])

      await store.fetchUsers(3, 10)

      expect(store.totalUsers).toBe(21)
    })

    it('stores the API detail and rethrows on failure', async () => {
      const store = useUsersStore()
      api.getUsers.mockRejectedValue(withDetail('Admins only'))

      await expect(store.fetchUsers()).rejects.toThrow('request failed')
      expect(store.error).toBe('Admins only')
      expect(store.loading).toBe(false)
    })

    it('uses a generic message without detail', async () => {
      const store = useUsersStore()
      api.getUsers.mockRejectedValue(new Error('net'))

      await expect(store.fetchUsers()).rejects.toThrow('net')
      expect(store.error).toBe('Failed to fetch users')
    })
  })

  describe('searchUsers', () => {
    it('stores results for a non-empty query', async () => {
      const store = useUsersStore()
      api.searchUsers.mockResolvedValue([user('found')])

      const result = await store.searchUsers('fo', 2, 5)

      expect(api.searchUsers).toHaveBeenCalledWith('fo', { skip: 5, limit: 5 })
      expect(result).toHaveLength(1)
      expect(store.searchQuery).toBe('fo')
      expect(store.searchResults.map(u => u.id)).toEqual(['found'])
    })

    it('clears search state for a blank query without calling the API', async () => {
      const store = useUsersStore()
      store.searchQuery = 'old'
      store.searchResults = [user('x')]

      await expect(store.searchUsers('   ')).resolves.toBeUndefined()

      expect(api.searchUsers).not.toHaveBeenCalled()
      expect(store.searchQuery).toBe('')
      expect(store.searchResults).toEqual([])
    })

    it('records the error and rethrows', async () => {
      const store = useUsersStore()
      api.searchUsers.mockRejectedValue(withDetail('Bad query'))

      await expect(store.searchUsers('x')).rejects.toThrow('request failed')
      expect(store.error).toBe('Bad query')

      api.searchUsers.mockRejectedValue(new Error('net'))
      await expect(store.searchUsers('x')).rejects.toThrow('net')
      expect(store.error).toBe('Failed to search users')
    })
  })

  describe('statistics and single user', () => {
    it('fetchUserStatistics stores the counters', async () => {
      const store = useUsersStore()
      api.getUserStatistics.mockResolvedValue({ total_users: 4, active_users: 3 })

      await expect(store.fetchUserStatistics()).resolves.toEqual({
        total_users: 4,
        active_users: 3
      })
      expect(store.statistics).toEqual({ total_users: 4, active_users: 3 })
    })

    it('fetchUserStatistics records errors and rethrows', async () => {
      const store = useUsersStore()
      api.getUserStatistics.mockRejectedValue(new Error('x'))

      await expect(store.fetchUserStatistics()).rejects.toThrow('x')
      expect(store.error).toBe('Failed to fetch user statistics')
    })

    it('fetchUser sets the selected user', async () => {
      const store = useUsersStore()
      api.getUser.mockResolvedValue(user('u1'))

      await expect(store.fetchUser('u1')).resolves.toEqual(user('u1'))
      expect(store.selectedUser?.id).toBe('u1')
    })

    it('fetchUser records errors and rethrows', async () => {
      const store = useUsersStore()
      api.getUser.mockRejectedValue(withDetail('Not found'))

      await expect(store.fetchUser('x')).rejects.toThrow('request failed')
      expect(store.error).toBe('Not found')
    })
  })

  describe('createUser', () => {
    it('prepends on the first page and updates statistics', async () => {
      const store = useUsersStore()
      store.users = [user('old')]
      store.statistics = { total_users: 2, active_users: 1 }
      api.createUser.mockResolvedValue(user('new'))

      await store.createUser({} as never)

      expect(store.users.map(u => u.id)).toEqual(['new', 'old'])
      expect(store.statistics).toEqual({ total_users: 3, active_users: 2 })
    })

    it('does not touch the list when not on the first page', async () => {
      const store = useUsersStore()
      store.currentPage = 2
      api.createUser.mockResolvedValue(user('new', { is_active: false }))

      await store.createUser({} as never)

      expect(store.users).toEqual([])
    })

    it('keeps active count when the new user is inactive', async () => {
      const store = useUsersStore()
      store.statistics = { total_users: 1, active_users: 1 }
      api.createUser.mockResolvedValue(user('new', { is_active: false }))

      await store.createUser({} as never)

      expect(store.statistics).toEqual({ total_users: 2, active_users: 1 })
    })

    it('records errors and rethrows', async () => {
      const store = useUsersStore()
      api.createUser.mockRejectedValue(withDetail('Email taken'))

      await expect(store.createUser({} as never)).rejects.toThrow('request failed')
      expect(store.error).toBe('Email taken')

      api.createUser.mockRejectedValue(new Error('net'))
      await expect(store.createUser({} as never)).rejects.toThrow('net')
      expect(store.error).toBe('Failed to create user')
    })
  })

  describe('updateUser', () => {
    it('replaces the list entry and the selected user', async () => {
      const store = useUsersStore()
      store.users = [user('u1')]
      store.selectedUser = user('u1')
      api.updateUser.mockResolvedValue(user('u1', { name: 'Renamed' }))

      await store.updateUser('u1', {} as never)

      expect(store.users[0]).toMatchObject({ name: 'Renamed' })
      expect(store.selectedUser).toMatchObject({ name: 'Renamed' })
    })

    it('leaves unrelated selection alone', async () => {
      const store = useUsersStore()
      store.selectedUser = user('other')
      api.updateUser.mockResolvedValue(user('u1'))

      await store.updateUser('u1', {} as never)

      expect(store.selectedUser?.id).toBe('other')
    })

    it('records errors and rethrows', async () => {
      const store = useUsersStore()
      api.updateUser.mockRejectedValue(withDetail('Locked'))

      await expect(store.updateUser('u1', {} as never)).rejects.toThrow('request failed')
      expect(store.error).toBe('Locked')

      api.updateUser.mockRejectedValue(new Error('net'))
      await expect(store.updateUser('u1', {} as never)).rejects.toThrow('net')
      expect(store.error).toBe('Failed to update user')
    })
  })

  describe('updateUserPassword', () => {
    it('returns the API response', async () => {
      const store = useUsersStore()
      api.updateUserPassword.mockResolvedValue({ message: 'ok' })

      await expect(store.updateUserPassword('u1', 'pw')).resolves.toEqual({ message: 'ok' })
      expect(api.updateUserPassword).toHaveBeenCalledWith('u1', 'pw')
    })

    it('records errors and rethrows', async () => {
      const store = useUsersStore()
      api.updateUserPassword.mockRejectedValue(withDetail('Weak'))

      await expect(store.updateUserPassword('u1', 'x')).rejects.toThrow('request failed')
      expect(store.error).toBe('Weak')

      api.updateUserPassword.mockRejectedValue(new Error('net'))
      await expect(store.updateUserPassword('u1', 'x')).rejects.toThrow('net')
      expect(store.error).toBe('Failed to update password')
    })
  })

  describe('activate / deactivate / delete', () => {
    it('activateUser flags the listed and selected user active', async () => {
      const store = useUsersStore()
      store.users = [user('u1', { is_active: false })]
      store.selectedUser = user('u1', { is_active: false })
      api.activateUser.mockResolvedValue({ message: 'ok' })

      await expect(store.activateUser('u1')).resolves.toEqual({ message: 'ok' })

      expect(store.users[0]?.is_active).toBe(true)
      expect(store.selectedUser?.is_active).toBe(true)
    })

    it('deactivateUser flags the listed and selected user inactive', async () => {
      const store = useUsersStore()
      store.users = [user('u1')]
      store.selectedUser = user('u1')
      api.deactivateUser.mockResolvedValue({ message: 'ok' })

      await store.deactivateUser('u1')

      expect(store.users[0]?.is_active).toBe(false)
      expect(store.selectedUser?.is_active).toBe(false)
    })

    it('activate and deactivate leave unlisted users alone and record errors', async () => {
      const store = useUsersStore()
      api.activateUser.mockResolvedValue({} as never)
      api.deactivateUser.mockResolvedValue({} as never)

      await store.activateUser('ghost')
      await store.deactivateUser('ghost')
      expect(store.users).toEqual([])

      api.activateUser.mockRejectedValue(withDetail('No'))
      await expect(store.activateUser('u1')).rejects.toThrow('request failed')
      expect(store.error).toBe('No')

      api.deactivateUser.mockRejectedValue(new Error('net'))
      await expect(store.deactivateUser('u1')).rejects.toThrow('net')
      expect(store.error).toBe('Failed to deactivate user')
    })

    it('activateUser records a generic message without detail', async () => {
      const store = useUsersStore()
      api.activateUser.mockRejectedValue(new Error('net'))

      await expect(store.activateUser('u1')).rejects.toThrow('net')
      expect(store.error).toBe('Failed to activate user')
    })

    it('deleteUser removes the user, clears selection and decrements the total', async () => {
      const store = useUsersStore()
      store.users = [user('u1'), user('u2')]
      store.selectedUser = user('u1')
      store.statistics = { total_users: 2 }
      api.deleteUser.mockResolvedValue({ message: 'deleted' })

      await expect(store.deleteUser('u1')).resolves.toEqual({ message: 'deleted' })

      expect(store.users.map(u => u.id)).toEqual(['u2'])
      expect(store.selectedUser).toBeNull()
      expect(store.statistics.total_users).toBe(1)
    })

    it('deleteUser keeps unrelated selection and records errors', async () => {
      const store = useUsersStore()
      store.selectedUser = user('keep')
      api.deleteUser.mockResolvedValueOnce({})
      await store.deleteUser('u1')
      expect(store.selectedUser?.id).toBe('keep')

      api.deleteUser.mockRejectedValueOnce(withDetail('Last admin'))
      await expect(store.deleteUser('u1')).rejects.toThrow('request failed')
      expect(store.error).toBe('Last admin')

      api.deleteUser.mockRejectedValueOnce(new Error('net'))
      await expect(store.deleteUser('u1')).rejects.toThrow('net')
      expect(store.error).toBe('Failed to delete user')
    })
  })

  describe('fetchUserActivity', () => {
    it('returns the activity and records errors', async () => {
      const store = useUsersStore()
      api.getUserActivity.mockResolvedValue({ login_count: 3 })

      await expect(store.fetchUserActivity('u1')).resolves.toEqual({ login_count: 3 })

      api.getUserActivity.mockRejectedValue(withDetail('Forbidden'))
      await expect(store.fetchUserActivity('u1')).rejects.toThrow('request failed')
      expect(store.error).toBe('Forbidden')

      api.getUserActivity.mockRejectedValue(new Error('net'))
      await expect(store.fetchUserActivity('u1')).rejects.toThrow('net')
      expect(store.error).toBe('Failed to fetch user activity')
    })
  })

  describe('clearing and $reset', () => {
    it('clearSearch, clearError and clearSelectedUser reset their slices', () => {
      const store = useUsersStore()
      store.searchQuery = 'q'
      store.searchResults = [user('x')]
      store.error = 'x'
      store.selectedUser = user('u1')

      store.clearSearch()
      expect(store.searchQuery).toBe('')
      expect(store.searchResults).toEqual([])

      store.clearError()
      expect(store.error).toBeNull()

      store.clearSelectedUser()
      expect(store.selectedUser).toBeNull()
    })

    it('$reset restores every slice', () => {
      const store = useUsersStore()
      store.users = [user('u1')]
      store.statistics = { total_users: 9 }
      store.loading = true
      store.error = 'x'
      store.currentPage = 4
      store.itemsPerPage = 50
      store.totalUsers = 99
      store.searchQuery = 'q'
      store.searchResults = [user('s')]

      store.$reset()

      expect(store.users).toEqual([])
      expect(store.statistics).toEqual({})
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.currentPage).toBe(1)
      expect(store.itemsPerPage).toBe(10)
      expect(store.totalUsers).toBe(0)
      expect(store.searchQuery).toBe('')
      expect(store.searchResults).toEqual([])
    })
  })
})
