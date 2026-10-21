<!--
  Scope Create View

  **New View** - Built with DRY/SOLID principles

  **DRY Improvements**:
  - Uses useScopeUtils composable (scope name validation)
  - Uses refactored useScopesStore with service layer

  **SOLID-SRP**:
  - View: Form UI and user interactions
  - Store: State management
  - Service: Network calls
  - Composables: Reusable utility functions

  **Features**:
  - Create new clinical scope
  - Validate scope name format (lowercase-with-dashes)
  - Set public/private visibility
  - Auto-navigate to new scope dashboard

  @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-42-create-scope-view
-->

<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-folder-plus</v-icon>
            Create new scope
          </v-card-title>

          <v-card-text>
            <v-form ref="formRef" v-model="valid" @submit.prevent="handleSubmit">
              <!-- Scope Name (machine-readable) -->
              <v-text-field
                v-model="scopeData.name"
                label="Scope Name (machine-readable)"
                :rules="nameRules"
                :error="nameExists"
                hint="lowercase-with-dashes, e.g., kidney-genetics"
                persistent-hint
                prepend-icon="mdi-identifier"
                required
                @blur="validateName"
              >
                <template #append-inner>
                  <v-progress-circular
                    v-if="checkingName"
                    indeterminate
                    size="20"
                    width="2"
                    color="primary"
                  ></v-progress-circular>
                  <v-icon
                    v-else-if="scopeData.name && !nameExists && isValidScopeName(scopeData.name)"
                    icon="mdi-check-circle"
                    color="success"
                  ></v-icon>
                  <v-icon
                    v-else-if="nameExists"
                    icon="mdi-alert-circle-outline"
                    color="error"
                  ></v-icon>
                  <v-icon
                    v-else-if="scopeData.name"
                    icon="mdi-alert-circle"
                    color="warning"
                  ></v-icon>
                </template>
              </v-text-field>

              <!-- Display Name (human-readable) -->
              <v-text-field
                v-model="scopeData.display_name"
                label="Display Name"
                :rules="displayNameRules"
                hint="Human-readable name, e.g., Kidney Genetics"
                persistent-hint
                prepend-icon="mdi-format-title"
                required
              ></v-text-field>

              <v-select
                v-model="scopeData.default_workflow_pair_id"
                :items="workflowPairs"
                item-title="displayName"
                item-value="id"
                label="Methodology"
                :rules="[v => !!v || 'Choose a methodology']"
                :loading="loadingWorkflowPairs"
                hint="Workflow pair that defines the precuration and curation schemas"
                persistent-hint
                prepend-icon="mdi-sitemap"
              ></v-select>

              <!-- Description -->
              <v-textarea
                v-model="scopeData.description"
                label="Description"
                rows="3"
                prepend-icon="mdi-text"
                hint="Brief description of this clinical scope"
                persistent-hint
              ></v-textarea>

              <!-- Institution (optional) -->
              <v-text-field
                v-model="scopeData.institution"
                label="Institution (optional)"
                prepend-icon="mdi-hospital-building"
                hint="e.g., University Hospital"
                persistent-hint
              ></v-text-field>

              <!-- Public/Private -->
              <v-switch
                v-model="scopeData.is_public"
                label="Public Scope"
                color="primary"
                hint="Public scopes are visible to all users"
                persistent-hint
              >
                <template #prepend>
                  <v-icon :icon="getScopeVisibilityIcon(scopeData.is_public)"></v-icon>
                </template>
              </v-switch>
            </v-form>

            <!-- Initial Members Section -->
            <v-divider class="my-4" />

            <div class="d-flex align-center mb-3">
              <v-icon start color="primary">mdi-account-group</v-icon>
              <span class="text-subtitle-1 font-weight-medium">Initial Members (Optional)</span>
            </div>

            <p class="text-body-2 text-medium-emphasis mb-3">
              Add team members who will be invited when the scope is created. You'll be added as an
              admin automatically.
            </p>

            <!-- Pending members list -->
            <v-list v-if="pendingMembers.length > 0" density="compact" class="mb-3">
              <v-list-item v-for="member in pendingMembers" :key="member.user.id">
                <template #prepend>
                  <v-avatar size="32" :color="getRoleColor(member.role)">
                    <span class="text-caption">{{ getInitials(member.user.name) }}</span>
                  </v-avatar>
                </template>

                <v-list-item-title>{{ member.user.name || member.user.email }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ member.user.email }} - {{ member.role }}
                </v-list-item-subtitle>

                <template #append>
                  <v-btn
                    aria-label="Remove member"
                    icon="mdi-close"
                    size="small"
                    variant="text"
                    @click="removePendingMember(member.user.id)"
                  />
                </template>
              </v-list-item>
            </v-list>

            <!-- Add member button -->
            <v-btn
              variant="outlined"
              color="primary"
              prepend-icon="mdi-account-plus"
              @click="showAddMemberDialog = true"
            >
              Add member
            </v-btn>
          </v-card-text>

          <v-card-actions>
            <v-btn variant="outlined" @click="cancel"> Cancel </v-btn>
            <v-spacer />
            <v-btn
              color="primary"
              :disabled="!valid || loading"
              :loading="loading"
              @click="handleSubmit"
            >
              <v-icon start>mdi-check</v-icon>
              Create scope
            </v-btn>
          </v-card-actions>
        </v-card>

        <ScopeNamingHelp />
      </v-col>
    </v-row>

    <!-- Add Member Dialog for Initial Members -->
    <v-dialog v-model="showAddMemberDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start color="primary">mdi-account-plus</v-icon>
          Add initial member
        </v-card-title>

        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            Search for existing users to invite when this scope is created.
          </v-alert>

          <!-- Simple user search for scope creation -->
          <v-autocomplete
            v-model="selectedMember"
            :items="userSearchResults"
            :loading="searchingUsers"
            item-title="displayName"
            item-value="id"
            label="Search for user"
            placeholder="Type name or email..."
            return-object
            clearable
            no-filter
            @update:search="onUserSearch"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props" :title="undefined">
                <v-list-item-title>{{ item.name || item.email }}</v-list-item-title>
                <v-list-item-subtitle>{{ item.email }}</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-autocomplete>

          <!-- Role selection -->
          <v-select v-model="memberRole" :items="roleOptions" label="Role" class="mt-3">
            <template #item="{ item, props }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon :icon="getRoleIcon(item)" :color="getRoleColor(item)" />
                </template>
              </v-list-item>
            </template>
          </v-select>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelAddMember">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!selectedMember || !memberRole"
            @click="addPendingMember"
          >
            Add
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="showSnackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
      <template #actions>
        <v-btn color="white" variant="text" @click="showSnackbar = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed, watch, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useScopesStore, type ScopeRole } from '@/stores/scopes'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useLogger } from '@/composables/useLogger'
  import { usersApi } from '@/api/users'
  import { useWorkflowPairs } from '@/components/scope/useWorkflowPairs'
  import ScopeNamingHelp from './ScopeNamingHelp.vue'
  import { getInitials, displayNameRules } from './ScopeCreate.utils'
  import type {
    ErrorLike,
    PendingMember,
    ScopeFormData,
    SearchUser,
    UserRecord
  } from './ScopeCreate.types'

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const router = useRouter()
  const scopeStore = useScopesStore()
  const { isValidScopeName, getScopeVisibilityIcon } = useScopeUtils()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const logger = useLogger()

  // ============================================
  // LIFECYCLE
  // ============================================

  /**
   * Load existing scopes on mount for name validation
   */
  onMounted(async () => {
    loadWorkflowPairs()
    try {
      if (scopeStore.scopes.length === 0) {
        logger.debug('Loading existing scopes for name validation')
        await scopeStore.fetchUserScopes()
      }
    } catch (error) {
      logger.error('Failed to load existing scopes', { error: (error as ErrorLike).message })
      // Don't block the user from creating a scope if we can't load existing ones
    }
  })

  // ============================================
  // STATE
  // ============================================

  const formRef = ref<{ validate: () => unknown } | null>(null)
  const valid = ref(false)
  const loading = ref(false)
  const checkingName = ref(false)
  const nameExists = ref(false)

  const scopeData = ref<ScopeFormData>({
    name: '',
    display_name: '',
    description: '',
    institution: '',
    is_public: false,
    default_workflow_pair_id: null
  })

  // Snackbar
  const showSnackbar = ref(false)
  const snackbarMessage = ref('')
  const snackbarColor = ref('success')

  const {
    workflowPairs,
    loading: loadingWorkflowPairs,
    loadWorkflowPairs
  } = useWorkflowPairs(message => {
    snackbarMessage.value = message
    snackbarColor.value = 'error'
    showSnackbar.value = true
  })

  // Initial members
  const showAddMemberDialog = ref(false)
  const pendingMembers = ref<PendingMember[]>([])
  const selectedMember = ref<SearchUser | null>(null)
  const memberRole = ref<ScopeRole>('curator')
  const userSearchResults = ref<SearchUser[]>([])
  const searchingUsers = ref(false)
  const searchDebounce = ref<ReturnType<typeof setTimeout> | null>(null)

  const roleOptions: ScopeRole[] = ['admin', 'curator', 'reviewer', 'viewer']

  // ============================================
  // COMPUTED
  // ============================================

  /**
   * Check if scope name already exists in the store
   */
  const scopeNameExists = computed(() => {
    if (!scopeData.value.name) return false
    return scopeStore.scopes.some(s => s.name === scopeData.value.name.toLowerCase())
  })

  // ============================================
  // WATCHERS
  // ============================================

  /**
   * Watch for scope name changes and validate in real-time
   */
  watch(
    () => scopeData.value.name,
    newName => {
      if (newName && isValidScopeName(newName)) {
        // Check if name exists
        nameExists.value = scopeNameExists.value

        if (nameExists.value) {
          logger.warn('Scope name already exists', { name: newName })
          showNotification(
            `Scope "${newName}" already exists. Please choose a different name.`,
            'warning'
          )
        }
      } else {
        nameExists.value = false
      }
    },
    { immediate: false }
  )

  // ============================================
  // VALIDATION RULES
  // ============================================

  const nameRules = [
    (v: string) => !!v || 'Scope name is required',
    (v: string) => isValidScopeName(v) || 'Must be 4-64 chars, lowercase letters and dashes only',
    (v: string) => !v.includes('--') || 'No consecutive dashes allowed',
    (v: string) => /^[a-z]/.test(v) || 'Must start with a lowercase letter',
    (v: string) => /[a-z0-9]$/.test(v) || 'Must end with a letter or number',
    () =>
      !scopeNameExists.value || 'This scope name already exists. Please choose a different name.'
  ]

  // ============================================
  // METHODS
  // ============================================

  /**
   * Validate scope name on blur
   */
  const validateName = () => {
    if (formRef.value) {
      formRef.value.validate()
    }
  }

  /**
   * Handle form submission
   */
  const handleSubmit = async () => {
    if (!valid.value) return

    loading.value = true

    try {
      logger.debug('Creating new scope', {
        name: scopeData.value.name,
        display_name: scopeData.value.display_name,
        initial_members: pendingMembers.value.length
      })

      const { default_workflow_pair_id: methodology, ...rest } = scopeData.value
      if (!methodology) return
      const newScope = await scopeStore.createScope({
        ...rest,
        default_workflow_pair_id: methodology
      })

      logger.info('Scope created successfully', {
        scope_id: newScope.id,
        name: newScope.name
      })

      // Invite pending members
      if (pendingMembers.value.length > 0) {
        logger.debug('Inviting initial members', {
          scope_id: newScope.id,
          count: pendingMembers.value.length
        })

        for (const member of pendingMembers.value) {
          try {
            await scopeStore.inviteMember(newScope.id, {
              user_id: member.user.id,
              role: member.role
            })
            logger.debug('Invited member', {
              scope_id: newScope.id,
              user_id: member.user.id,
              role: member.role
            })
          } catch (inviteError) {
            logger.warn('Failed to invite member', {
              scope_id: newScope.id,
              user_id: member.user.id,
              error: (inviteError as ErrorLike).message
            })
            // Continue with other invitations even if one fails
          }
        }
      }

      showNotification('Scope created successfully!', 'success')

      // Navigate to the new scope dashboard after a brief delay
      setTimeout(() => {
        router.push({
          name: 'scope-dashboard',
          params: { scopeId: newScope.id }
        })
      }, 1000)
    } catch (error) {
      // Extract detailed error message from API response
      const err = error as ErrorLike
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message

      logger.error('Failed to create scope', {
        error: err.message,
        stack: err.stack,
        scope_data: scopeData.value,
        api_error: errorMessage
      })

      showNotification(`Failed to create scope: ${errorMessage}`, 'error')
    } finally {
      loading.value = false
    }
  }

  /**
   * Cancel and go back
   */
  const cancel = () => {
    logger.debug('Scope creation cancelled')
    router.back()
  }

  /**
   * Show notification snackbar
   */
  const showNotification = (message: string, color = 'success') => {
    snackbarMessage.value = message
    snackbarColor.value = color
    showSnackbar.value = true
  }

  // ============================================
  // INITIAL MEMBERS METHODS
  // ============================================

  /**
   * Handle user search with debounce
   */
  const onUserSearch = (query: string) => {
    if (searchDebounce.value) {
      clearTimeout(searchDebounce.value)
    }

    if (!query || query.length < 2) {
      userSearchResults.value = []
      return
    }

    searchDebounce.value = setTimeout(async () => {
      searchingUsers.value = true
      try {
        const results = (await usersApi.searchUsers(query, { limit: 10 })) as UserRecord[]
        // Filter out already added members
        const existingIds = pendingMembers.value.map(m => m.user.id)
        userSearchResults.value = results
          .filter(u => !existingIds.includes(u.id))
          .map(u => ({ ...u, displayName: u.name || u.email }))
      } catch (error) {
        logger.error('User search failed', { error: (error as ErrorLike).message })
        userSearchResults.value = []
      } finally {
        searchingUsers.value = false
      }
    }, 300)
  }

  /**
   * Add member to pending list
   */
  const addPendingMember = () => {
    if (!selectedMember.value || !memberRole.value) return

    pendingMembers.value.push({
      user: selectedMember.value,
      role: memberRole.value
    })

    logger.debug('Added pending member', {
      userId: selectedMember.value.id,
      role: memberRole.value
    })

    cancelAddMember()
  }

  /**
   * Remove member from pending list
   */
  const removePendingMember = (userId: string) => {
    pendingMembers.value = pendingMembers.value.filter(m => m.user.id !== userId)
  }

  /**
   * Cancel add member dialog
   */
  const cancelAddMember = () => {
    showAddMemberDialog.value = false
    selectedMember.value = null
    memberRole.value = 'curator'
    userSearchResults.value = []
  }
</script>

<style scoped>
  /* Form spacing */
  .v-text-field,
  .v-textarea,
  .v-switch {
    margin-bottom: 16px;
  }

  /* Help list */
  .v-list-item {
    min-height: 40px;
  }
</style>
