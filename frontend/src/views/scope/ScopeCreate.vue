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
        <v-card variant="flat" border>
          <v-card-title>New scope</v-card-title>
          <v-card-subtitle>You become the scope admin.</v-card-subtitle>

          <v-card-text>
            <v-form
              ref="formRef"
              v-model="valid"
              validate-on="blur lazy"
              @submit.prevent="handleSubmit"
            >
              <v-text-field
                v-model="scopeData.display_name"
                label="Display name"
                :rules="displayNameRules"
                hint="Human-readable name, e.g. Kidney Genetics"
                persistent-hint
                autofocus
                required
              ></v-text-field>

              <!-- Derived from the display name until the user edits it -->
              <v-text-field
                ref="nameField"
                v-model="scopeData.name"
                label="URL name"
                :rules="nameRules"
                :error="nameExists"
                hint="Lowercase letters, digits and single dashes, 4-64 characters. Filled in from the display name."
                persistent-hint
                required
                @update:model-value="slugEdited = true"
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
                </template>
              </v-text-field>

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
              ></v-select>

              <!-- Description -->
              <v-textarea v-model="scopeData.description" label="Description" rows="2"></v-textarea>

              <!-- Institution (optional) -->
              <v-text-field
                v-model="scopeData.institution"
                label="Institution (optional)"
              ></v-text-field>

              <!-- Public/Private -->
              <v-switch
                v-model="scopeData.is_public"
                label="Public scope"
                color="primary"
                hint="Public scopes are visible to all users"
                persistent-hint
              ></v-switch>
            </v-form>

            <!-- Members are invited after creation: user search needs scope admin -->
            <p class="text-body-medium text-medium-emphasis mt-4">
              You'll be the scope admin. After creating the scope, invite members from its Members
              tab.
            </p>
          </v-card-text>

          <v-card-actions>
            <v-btn variant="text" @click="cancel"> Cancel </v-btn>
            <v-spacer />
            <v-btn color="primary" variant="flat" :loading="loading" @click="handleSubmit">
              Create scope
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed, watch, onMounted, nextTick } from 'vue'
  import { useRouter } from 'vue-router'
  import { useScopesStore } from '@/stores/scopes'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useLogger } from '@/composables/useLogger'
  import { useWorkflowPairs } from '@/components/scope/useWorkflowPairs'
  import { showError, showSnackbar } from '@/composables/useNotifications'
  import { displayNameRules, slugify } from './ScopeCreate.utils'
  import type { ErrorLike, ScopeFormData } from './ScopeCreate.types'

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const router = useRouter()
  const scopeStore = useScopesStore()
  const { isValidScopeName } = useScopeUtils()
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
  const slugEdited = ref(false)
  const nameField = ref<{ errorMessages: string[]; validate: () => Promise<unknown> } | null>(null)

  const scopeData = ref<ScopeFormData>({
    name: '',
    display_name: '',
    description: '',
    institution: '',
    is_public: false,
    default_workflow_pair_id: null
  })

  const {
    workflowPairs,
    loading: loadingWorkflowPairs,
    loadWorkflowPairs
  } = useWorkflowPairs(message => showError(message))

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

  watch(
    () => scopeData.value.display_name,
    text => {
      if (slugEdited.value) return
      scopeData.value.name = slugify(text)
      // A filled-in name must not keep showing "required": re-check it, but only if it showed an error
      void nextTick(() => {
        if (nameField.value?.errorMessages.length) void nameField.value.validate()
      })
    }
  )

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
    const result = (await formRef.value?.validate()) as { valid: boolean } | undefined
    if (result ? !result.valid : !valid.value) return

    loading.value = true

    try {
      logger.debug('Creating new scope', {
        name: scopeData.value.name,
        display_name: scopeData.value.display_name
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

      showNotification('Scope created', 'success')

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
    showSnackbar(message, color)
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
