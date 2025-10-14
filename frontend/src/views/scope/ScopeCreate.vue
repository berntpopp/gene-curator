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
  - Optional due date
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
            Create New Scope
          </v-card-title>

          <v-card-text>
            <v-form ref="formRef" v-model="valid" @submit.prevent="handleSubmit">
              <!-- Scope Name (machine-readable) -->
              <v-text-field
                v-model="scopeData.name"
                label="Scope Name (machine-readable)"
                :rules="nameRules"
                hint="lowercase-with-dashes, e.g., kidney-genetics"
                persistent-hint
                prepend-icon="mdi-identifier"
                required
                @blur="validateName"
              >
                <template #append-inner>
                  <v-icon
                    v-if="scopeData.name && isValidScopeName(scopeData.name)"
                    icon="mdi-check-circle"
                    color="success"
                  ></v-icon>
                  <v-icon v-else-if="scopeData.name" icon="mdi-alert-circle" color="error"></v-icon>
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

              <!-- Due Date (optional) -->
              <v-text-field
                v-model="scopeData.due_date"
                label="Due Date (optional)"
                type="date"
                prepend-icon="mdi-calendar"
                hint="Optional deadline for this scope"
                persistent-hint
              ></v-text-field>

              <!-- Active Status -->
              <v-switch
                v-model="scopeData.is_active"
                label="Active Scope"
                color="success"
                hint="Active scopes are visible to curators"
                persistent-hint
              >
                <template #prepend>
                  <v-icon
                    :icon="scopeData.is_active ? 'mdi-check-circle' : 'mdi-pause-circle'"
                  ></v-icon>
                </template>
              </v-switch>
            </v-form>
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
              Create Scope
            </v-btn>
          </v-card-actions>
        </v-card>

        <!-- Help Card -->
        <v-card class="mt-4">
          <v-card-title>
            <v-icon start>mdi-help-circle</v-icon>
            Scope Naming Guidelines
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-check" color="success"></v-icon>
                </template>
                <v-list-item-title> Use lowercase letters (a-z) </v-list-item-title>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-check" color="success"></v-icon>
                </template>
                <v-list-item-title> Separate words with dashes (-) </v-list-item-title>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-check" color="success"></v-icon>
                </template>
                <v-list-item-title> Length: 4-64 characters </v-list-item-title>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-close" color="error"></v-icon>
                </template>
                <v-list-item-title> No consecutive dashes (--) </v-list-item-title>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon icon="mdi-close" color="error"></v-icon>
                </template>
                <v-list-item-title> No spaces or special characters </v-list-item-title>
              </v-list-item>
            </v-list>

            <v-divider class="my-2" />

            <div class="text-caption text-medium-emphasis">
              <strong>Examples:</strong>
              <ul>
                <li>kidney-genetics</li>
                <li>cardio-genetics</li>
                <li>neuro-oncology</li>
              </ul>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="showSnackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
      <template #actions>
        <v-btn color="white" variant="text" @click="showSnackbar = false"> Close </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
  import { ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { useScopesStore } from '@/stores/scopes'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useLogger } from '@/composables/useLogger'

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const router = useRouter()
  const scopeStore = useScopesStore()
  const { isValidScopeName, getScopeVisibilityIcon } = useScopeUtils()
  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const formRef = ref(null)
  const valid = ref(false)
  const loading = ref(false)

  const scopeData = ref({
    name: '',
    display_name: '',
    description: '',
    institution: '',
    is_public: false,
    is_active: true,
    due_date: null
  })

  // Snackbar
  const showSnackbar = ref(false)
  const snackbarMessage = ref('')
  const snackbarColor = ref('success')

  // ============================================
  // VALIDATION RULES
  // ============================================

  const nameRules = [
    v => !!v || 'Scope name is required',
    v => isValidScopeName(v) || 'Must be 4-64 chars, lowercase letters and dashes only',
    v => !v.includes('--') || 'No consecutive dashes allowed',
    v => /^[a-z]/.test(v) || 'Must start with a lowercase letter',
    v => /[a-z0-9]$/.test(v) || 'Must end with a letter or number'
  ]

  const displayNameRules = [
    v => !!v || 'Display name is required',
    v => (v && v.length >= 4) || 'Minimum 4 characters required',
    v => (v && v.length <= 100) || 'Maximum 100 characters allowed'
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
        display_name: scopeData.value.display_name
      })

      const newScope = await scopeStore.createScope(scopeData.value)

      logger.info('Scope created successfully', {
        scope_id: newScope.id,
        name: newScope.name
      })

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
      const errorMessage =
        error.response?.data?.detail || error.response?.data?.message || error.message

      logger.error('Failed to create scope', {
        error: error.message,
        stack: error.stack,
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
  const showNotification = (message, color = 'success') => {
    snackbarMessage.value = message
    snackbarColor.value = color
    showSnackbar.value = true
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
