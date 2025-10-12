<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <div class="d-flex justify-space-between align-center mb-6">
          <div>
            <h1 class="text-h4 font-weight-bold">User Management</h1>
            <p class="text-subtitle-1 text-medium-emphasis mt-1">
              Manage user accounts, roles, and permissions
            </p>
          </div>
          <v-btn
            color="primary"
            prepend-icon="mdi-account-plus"
            size="large"
            @click="openCreateUserDialog"
          >
            Create User
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Statistics Cards -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <v-card class="h-100">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="primary" size="32" class="me-3">mdi-account-group</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">
                  {{ usersStore.statistics.total_users || 0 }}
                </div>
                <div class="text-caption text-medium-emphasis">Total Users</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="h-100">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="success" size="32" class="me-3">mdi-account-check</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">
                  {{ usersStore.statistics.active_users || 0 }}
                </div>
                <div class="text-caption text-medium-emphasis">Active Users</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="h-100">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="warning" size="32" class="me-3">mdi-account-off</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">
                  {{ usersStore.statistics.inactive_users || 0 }}
                </div>
                <div class="text-caption text-medium-emphasis">Inactive Users</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="h-100">
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon color="info" size="32" class="me-3">mdi-account-clock</v-icon>
              <div>
                <div class="text-h5 font-weight-bold">
                  {{ usersStore.statistics.recent_registrations || 0 }}
                </div>
                <div class="text-caption text-medium-emphasis">Recent (30d)</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Search and Filters -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="searchQuery"
          label="Search users..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          hide-details
          clearable
          @input="debouncedSearch"
          @click:clear="clearSearch"
        />
      </v-col>
      <v-col cols="12" md="6" class="d-flex align-center justify-end">
        <v-btn
          :loading="usersStore.loading"
          variant="outlined"
          prepend-icon="mdi-refresh"
          @click="refreshUsers"
        >
          Refresh
        </v-btn>
      </v-col>
    </v-row>

    <!-- Users Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="usersStore.paginatedUsers"
        :loading="usersStore.loading"
        loading-text="Loading users..."
        no-data-text="No users found"
        :items-per-page="usersStore.itemsPerPage"
        :page="usersStore.currentPage"
        @update:page="usersStore.currentPage = $event"
        @update:items-per-page="usersStore.itemsPerPage = $event"
      >
        <!-- User info -->
        <template #item.name="{ item }">
          <div class="d-flex align-center">
            <v-avatar size="32" class="me-3">
              <v-icon>mdi-account</v-icon>
            </v-avatar>
            <div>
              <div class="font-weight-medium">{{ item.name }}</div>
              <div class="text-caption text-medium-emphasis">{{ item.email }}</div>
            </div>
          </div>
        </template>

        <!-- Role -->
        <template #item.role="{ item }">
          <v-chip :color="getRoleColor(item.role)" size="small" variant="flat">
            <v-icon start size="14">{{ getRoleIcon(item.role) }}</v-icon>
            {{ item.role }}
          </v-chip>
        </template>

        <!-- Status -->
        <template #item.is_active="{ item }">
          <v-chip :color="item.is_active ? 'success' : 'error'" size="small" variant="flat">
            <v-icon start size="14">
              {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
            </v-icon>
            {{ item.is_active ? 'Active' : 'Inactive' }}
          </v-chip>
        </template>

        <!-- Dates -->
        <template #item.created_at="{ item }">
          <div class="text-body-2">
            {{ formatDate(item.created_at) }}
          </div>
        </template>

        <template #item.last_login="{ item }">
          <div class="text-body-2">
            {{ item.last_login ? formatDate(item.last_login) : 'Never' }}
          </div>
        </template>

        <!-- Actions -->
        <template #item.actions="{ item }">
          <v-menu>
            <template #activator="{ props }">
              <v-btn icon="mdi-dots-vertical" variant="text" size="small" v-bind="props" />
            </template>
            <v-list>
              <v-list-item @click="viewUser(item)">
                <template #prepend>
                  <v-icon>mdi-eye</v-icon>
                </template>
                <v-list-item-title>View Details</v-list-item-title>
              </v-list-item>
              <v-list-item @click="editUser(item)">
                <template #prepend>
                  <v-icon>mdi-pencil</v-icon>
                </template>
                <v-list-item-title>Edit User</v-list-item-title>
              </v-list-item>
              <v-list-item @click="resetPassword(item)">
                <template #prepend>
                  <v-icon>mdi-lock-reset</v-icon>
                </template>
                <v-list-item-title>Reset Password</v-list-item-title>
              </v-list-item>
              <v-divider />
              <v-list-item v-if="item.is_active" class="text-warning" @click="deactivateUser(item)">
                <template #prepend>
                  <v-icon color="warning">mdi-account-off</v-icon>
                </template>
                <v-list-item-title>Deactivate</v-list-item-title>
              </v-list-item>
              <v-list-item v-else class="text-success" @click="activateUser(item)">
                <template #prepend>
                  <v-icon color="success">mdi-account-check</v-icon>
                </template>
                <v-list-item-title>Activate</v-list-item-title>
              </v-list-item>
              <v-divider />
              <v-list-item class="text-error" @click="confirmDeleteUser(item)">
                <template #prepend>
                  <v-icon color="error">mdi-delete</v-icon>
                </template>
                <v-list-item-title>Delete User</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit User Dialog -->
    <v-dialog v-model="userDialog" max-width="600">
      <v-card>
        <v-card-title class="text-h5">
          {{ editingUser ? 'Edit User' : 'Create New User' }}
        </v-card-title>
        <v-card-text>
          <v-form ref="userForm" v-model="formValid" @submit.prevent="saveUser">
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="userFormData.name"
                  label="Full Name"
                  :rules="[rules.required]"
                  variant="outlined"
                  required
                />
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="userFormData.email"
                  label="Email"
                  type="email"
                  :rules="[rules.required, rules.email]"
                  variant="outlined"
                  required
                />
              </v-col>
              <v-col cols="12">
                <v-select
                  v-model="userFormData.role"
                  :items="roleOptions"
                  label="Role"
                  :rules="[rules.required]"
                  variant="outlined"
                  required
                />
              </v-col>
              <v-col v-if="!editingUser" cols="12">
                <v-text-field
                  v-model="userFormData.password"
                  label="Password"
                  type="password"
                  :rules="[rules.required, rules.minLength]"
                  variant="outlined"
                  hint="Minimum 8 characters"
                  required
                />
              </v-col>
              <v-col cols="12">
                <v-switch v-model="userFormData.is_active" label="Active" color="success" inset />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="userDialog = false"> Cancel </v-btn>
          <v-btn
            :loading="usersStore.loading"
            :disabled="!formValid"
            color="primary"
            @click="saveUser"
          >
            {{ editingUser ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- User Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="800">
      <v-card v-if="selectedUser">
        <v-card-title class="text-h5"> User Details: {{ selectedUser.name }} </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <v-list>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-email</v-icon>
                  </template>
                  <v-list-item-title>{{ selectedUser.email }}</v-list-item-title>
                  <v-list-item-subtitle>Email</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-shield-account</v-icon>
                  </template>
                  <v-list-item-title>
                    <v-chip :color="getRoleColor(selectedUser.role)" size="small">
                      {{ selectedUser.role }}
                    </v-chip>
                  </v-list-item-title>
                  <v-list-item-subtitle>Role</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-clock</v-icon>
                  </template>
                  <v-list-item-title>{{ formatDate(selectedUser.created_at) }}</v-list-item-title>
                  <v-list-item-subtitle>Created</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-login</v-icon>
                  </template>
                  <v-list-item-title>
                    {{ selectedUser.last_login ? formatDate(selectedUser.last_login) : 'Never' }}
                  </v-list-item-title>
                  <v-list-item-subtitle>Last Login</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            <v-col v-if="userActivity" cols="12" md="6">
              <h3 class="mb-3">Activity Summary</h3>
              <v-list>
                <v-list-item>
                  <v-list-item-title>{{ userActivity.genes_created || 0 }}</v-list-item-title>
                  <v-list-item-subtitle>Genes Created</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>{{ userActivity.curations_created || 0 }}</v-list-item-title>
                  <v-list-item-subtitle>Curations Created</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>{{ userActivity.total_contributions || 0 }}</v-list-item-title>
                  <v-list-item-subtitle>Total Contributions</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="detailsDialog = false"> Close </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h5 text-error"> Confirm Delete </v-card-title>
        <v-card-text>
          Are you sure you want to delete user <strong>{{ userToDelete?.name }}</strong
          >? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false"> Cancel </v-btn>
          <v-btn :loading="usersStore.loading" color="error" @click="performDeleteUser">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for messages -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
  import { ref, onMounted, watch } from 'vue'
  import { useUsersStore } from '@/stores/users'

  // Simple debounce function
  function debounce(func, wait) {
    let timeout
    return function (...args) {
      const later = () => {
        clearTimeout(timeout)
        func.apply(this, args)
      }
      clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  }

  // Store
  const usersStore = useUsersStore()

  // Reactive state
  const searchQuery = ref('')
  const userDialog = ref(false)
  const detailsDialog = ref(false)
  const deleteDialog = ref(false)
  const editingUser = ref(null)
  const userToDelete = ref(null)
  const selectedUser = ref(null)
  const userActivity = ref(null)
  const formValid = ref(false)
  const userForm = ref(null)

  // Snackbar
  const snackbar = ref({
    show: false,
    message: '',
    color: 'success'
  })

  // Form data
  const userFormData = ref({
    name: '',
    email: '',
    role: 'viewer',
    password: '',
    is_active: true
  })

  // Store reactive properties (accessed directly without destructuring)
  // const { users, paginatedUsers, statistics, loading, error, currentPage, itemsPerPage } are accessed via usersStore.*

  // Table headers
  const headers = [
    { title: 'User', key: 'name', sortable: true },
    { title: 'Role', key: 'role', sortable: true },
    { title: 'Status', key: 'is_active', sortable: true },
    { title: 'Created', key: 'created_at', sortable: true },
    { title: 'Last Login', key: 'last_login', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false, width: '100' }
  ]

  // Role options
  const roleOptions = [
    { title: 'Viewer', value: 'viewer' },
    { title: 'Curator', value: 'curator' },
    { title: 'Admin', value: 'admin' }
  ]

  // Form validation rules
  const rules = {
    required: value => !!value || 'This field is required',
    email: value => {
      const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      return pattern.test(value) || 'Invalid email address'
    },
    minLength: value => (value && value.length >= 8) || 'Minimum 8 characters required'
  }

  // Debounced search
  const debouncedSearch = debounce(async query => {
    if (query) {
      await usersStore.searchUsers(query)
    } else {
      await usersStore.fetchUsers()
    }
  }, 300)

  // Methods
  function getRoleColor(role) {
    const roleColors = {
      admin: 'error',
      curator: 'warning',
      viewer: 'info'
    }
    return roleColors[role] || 'primary'
  }

  function getRoleIcon(role) {
    const roleIcons = {
      admin: 'mdi-shield-crown',
      curator: 'mdi-pencil',
      viewer: 'mdi-eye'
    }
    return roleIcons[role] || 'mdi-account'
  }

  function formatDate(date) {
    if (!date) return 'N/A'
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  async function refreshUsers() {
    try {
      await usersStore.fetchUsers()
      await usersStore.fetchUserStatistics()
      showSnackbar('Users refreshed successfully', 'success')
    } catch (error) {
      showSnackbar('Failed to refresh users', 'error')
    }
  }

  function clearSearch() {
    searchQuery.value = ''
    usersStore.clearSearch()
    usersStore.fetchUsers()
  }

  function openCreateUserDialog() {
    editingUser.value = null
    userFormData.value = {
      name: '',
      email: '',
      role: 'viewer',
      password: '',
      is_active: true
    }
    userDialog.value = true
  }

  function editUser(user) {
    editingUser.value = user
    userFormData.value = {
      name: user.name,
      email: user.email,
      role: user.role,
      password: '',
      is_active: user.is_active
    }
    userDialog.value = true
  }

  async function saveUser() {
    if (!userForm.value) return

    const { valid } = await userForm.value.validate()
    if (!valid) return

    try {
      if (editingUser.value) {
        // Update user
        const updateData = {
          name: userFormData.value.name,
          email: userFormData.value.email,
          role: userFormData.value.role,
          is_active: userFormData.value.is_active
        }
        await usersStore.updateUser(editingUser.value.id, updateData)
        showSnackbar('User updated successfully', 'success')
      } else {
        // Create user
        await usersStore.createUser(userFormData.value)
        showSnackbar('User created successfully', 'success')
      }
      userDialog.value = false
    } catch (error) {
      showSnackbar(error.message || 'Failed to save user', 'error')
    }
  }

  async function viewUser(user) {
    try {
      selectedUser.value = user
      userActivity.value = await usersStore.fetchUserActivity(user.id)
      detailsDialog.value = true
    } catch (error) {
      showSnackbar('Failed to load user details', 'error')
    }
  }

  async function activateUser(user) {
    try {
      await usersStore.activateUser(user.id)
      showSnackbar(`User ${user.name} activated successfully`, 'success')
    } catch (error) {
      showSnackbar('Failed to activate user', 'error')
    }
  }

  async function deactivateUser(user) {
    try {
      await usersStore.deactivateUser(user.id)
      showSnackbar(`User ${user.name} deactivated successfully`, 'warning')
    } catch (error) {
      showSnackbar('Failed to deactivate user', 'error')
    }
  }

  function confirmDeleteUser(user) {
    userToDelete.value = user
    deleteDialog.value = true
  }

  async function performDeleteUser() {
    if (!userToDelete.value) return

    try {
      await usersStore.deleteUser(userToDelete.value.id)
      showSnackbar(`User ${userToDelete.value.name} deleted successfully`, 'success')
      deleteDialog.value = false
      userToDelete.value = null
    } catch (error) {
      showSnackbar('Failed to delete user', 'error')
    }
  }

  async function resetPassword(user) {
    const newPassword = prompt(`Enter new password for ${user.name}:`)
    if (!newPassword || newPassword.length < 8) {
      showSnackbar('Password must be at least 8 characters long', 'error')
      return
    }

    try {
      await usersStore.updateUserPassword(user.id, newPassword)
      showSnackbar(`Password updated for ${user.name}`, 'success')
    } catch (error) {
      showSnackbar('Failed to update password', 'error')
    }
  }

  function showSnackbar(message, color = 'success') {
    snackbar.value = {
      show: true,
      message,
      color
    }
  }

  // Watch for errors
  watch(
    () => usersStore.error,
    newError => {
      if (newError) {
        showSnackbar(newError, 'error')
        usersStore.clearError()
      }
    }
  )

  // Initialize
  onMounted(async () => {
    try {
      await Promise.all([usersStore.fetchUsers(), usersStore.fetchUserStatistics()])
    } catch (error) {
      showSnackbar('Failed to load user data', 'error')
    }
  })
</script>

<style scoped>
  .v-card {
    transition: all 0.2s ease-in-out;
  }

  .v-card:hover {
    transform: translateY(-2px);
  }
</style>
