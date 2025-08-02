/**
 * User management store for admin operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { usersApi } from '@/api/users'

export const useUsersStore = defineStore('users', () => {
  // State
  const users = ref([])
  const selectedUser = ref(null)
  const statistics = ref({})
  const loading = ref(false)
  const error = ref(null)

  // Pagination state
  const currentPage = ref(1)
  const itemsPerPage = ref(10)
  const totalUsers = ref(0)

  // Search state
  const searchQuery = ref('')
  const searchResults = ref([])

  // Computed
  const paginatedUsers = computed(() => {
    if (searchQuery.value) {
      return searchResults.value
    }
    return users.value
  })

  const totalPages = computed(() => {
    return Math.ceil(totalUsers.value / itemsPerPage.value)
  })

  const hasNextPage = computed(() => {
    return currentPage.value < totalPages.value
  })

  const hasPreviousPage = computed(() => {
    return currentPage.value > 1
  })

  // Actions
  async function fetchUsers(page = 1, limit = 10) {
    loading.value = true
    error.value = null

    try {
      const skip = (page - 1) * limit
      const response = await usersApi.getUsers({ skip, limit })

      users.value = response
      currentPage.value = page
      itemsPerPage.value = limit

      // Note: API doesn't return total count, so we estimate
      totalUsers.value =
        response.length === limit ? page * limit + 1 : (page - 1) * limit + response.length

      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch users'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function searchUsers(query, page = 1, limit = 10) {
    if (!query.trim()) {
      searchQuery.value = ''
      searchResults.value = []
      return
    }

    loading.value = true
    error.value = null

    try {
      const skip = (page - 1) * limit
      const response = await usersApi.searchUsers(query, { skip, limit })

      searchQuery.value = query
      searchResults.value = response

      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to search users'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUserStatistics() {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.getUserStatistics()
      statistics.value = response
      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch user statistics'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUser(userId) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.getUser(userId)
      selectedUser.value = response
      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch user'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createUser(userData) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.createUser(userData)

      // Add to users list if we're on the first page
      if (currentPage.value === 1) {
        users.value.unshift(response)
      }

      // Update statistics if available
      if (statistics.value.total_users) {
        statistics.value.total_users += 1
        if (response.is_active && statistics.value.active_users) {
          statistics.value.active_users += 1
        }
      }

      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create user'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateUser(userId, userData) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.updateUser(userId, userData)

      // Update in users list
      const index = users.value.findIndex(user => user.id === userId)
      if (index !== -1) {
        users.value[index] = response
      }

      // Update selected user if it's the same
      if (selectedUser.value && selectedUser.value.id === userId) {
        selectedUser.value = response
      }

      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update user'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateUserPassword(userId, newPassword) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.updateUserPassword(userId, newPassword)
      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update password'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function activateUser(userId) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.activateUser(userId)

      // Update user in list
      const index = users.value.findIndex(user => user.id === userId)
      if (index !== -1) {
        users.value[index].is_active = true
      }

      // Update selected user
      if (selectedUser.value && selectedUser.value.id === userId) {
        selectedUser.value.is_active = true
      }

      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to activate user'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deactivateUser(userId) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.deactivateUser(userId)

      // Update user in list
      const index = users.value.findIndex(user => user.id === userId)
      if (index !== -1) {
        users.value[index].is_active = false
      }

      // Update selected user
      if (selectedUser.value && selectedUser.value.id === userId) {
        selectedUser.value.is_active = false
      }

      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to deactivate user'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteUser(userId) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.deleteUser(userId)

      // Remove from users list
      const index = users.value.findIndex(user => user.id === userId)
      if (index !== -1) {
        users.value.splice(index, 1)
      }

      // Clear selected user if it's the deleted one
      if (selectedUser.value && selectedUser.value.id === userId) {
        selectedUser.value = null
      }

      // Update statistics
      if (statistics.value.total_users) {
        statistics.value.total_users -= 1
      }

      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete user'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUserActivity(userId) {
    loading.value = true
    error.value = null

    try {
      const response = await usersApi.getUserActivity(userId)
      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch user activity'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearSearch() {
    searchQuery.value = ''
    searchResults.value = []
  }

  function clearError() {
    error.value = null
  }

  function clearSelectedUser() {
    selectedUser.value = null
  }

  // Reset store state
  function $reset() {
    users.value = []
    selectedUser.value = null
    statistics.value = {}
    loading.value = false
    error.value = null
    currentPage.value = 1
    itemsPerPage.value = 10
    totalUsers.value = 0
    searchQuery.value = ''
    searchResults.value = []
  }

  return {
    // State
    users,
    selectedUser,
    statistics,
    loading,
    error,
    currentPage,
    itemsPerPage,
    totalUsers,
    searchQuery,
    searchResults,

    // Computed
    paginatedUsers,
    totalPages,
    hasNextPage,
    hasPreviousPage,

    // Actions
    fetchUsers,
    searchUsers,
    fetchUserStatistics,
    fetchUser,
    createUser,
    updateUser,
    updateUserPassword,
    activateUser,
    deactivateUser,
    deleteUser,
    fetchUserActivity,
    clearSearch,
    clearError,
    clearSelectedUser,
    $reset
  }
})
