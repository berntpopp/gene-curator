<!--
  Scope Settings Component

  Configures scope-level settings including workflow pair selection.
  Per ClinGen SOP v11, the scope defines the methodology (workflow pair)
  that ALL genes in the scope follow.
-->

<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-cog</v-icon>
      Scope Settings
    </v-card-title>

    <v-card-text>
      <!-- Workflow Configuration Section -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="text-subtitle-1">
          <v-icon start size="small">mdi-sitemap</v-icon>
          Workflow Configuration
        </v-card-title>
        <v-card-text>
          <v-alert
            v-if="!scope.default_workflow_pair_id"
            type="warning"
            variant="tonal"
            class="mb-4"
          >
            <template #prepend>
              <v-icon>mdi-alert</v-icon>
            </template>
            <strong>No workflow configured.</strong>
            Select a workflow pair to enable precuration and curation for genes in this scope.
          </v-alert>

          <v-select
            v-model="selectedWorkflowPairId"
            :items="workflowPairs"
            item-title="displayName"
            item-value="id"
            label="Workflow Pair"
            hint="Defines the precuration and curation schemas for all genes in this scope"
            persistent-hint
            :loading="loadingWorkflowPairs"
            :disabled="saving || !canEditSettings"
            clearable
            @update:model-value="handleWorkflowPairChange"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #subtitle> {{ item.raw.version }} • {{ item.raw.description }} </template>
              </v-list-item>
            </template>
            <template #selection="{ item }">
              {{ item.raw.name }} ({{ item.raw.version }})
            </template>
          </v-select>

          <!-- Show linked schemas when workflow pair is selected -->
          <div v-if="selectedWorkflowPair" class="mt-4">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">Linked Schemas</div>
            <v-row dense>
              <v-col cols="12" md="6">
                <v-card variant="tonal" color="primary">
                  <v-card-text class="py-2">
                    <div class="text-caption text-medium-emphasis">Precuration Schema</div>
                    <div class="text-body-2 font-weight-medium">
                      {{ selectedWorkflowPair.precuration_schema_name || 'Not configured' }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="tonal" color="secondary">
                  <v-card-text class="py-2">
                    <div class="text-caption text-medium-emphasis">Curation Schema</div>
                    <div class="text-body-2 font-weight-medium">
                      {{ selectedWorkflowPair.curation_schema_name || 'Not configured' }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </div>
        </v-card-text>
      </v-card>

      <!-- Basic Information Section -->
      <v-card variant="outlined" class="mb-4">
        <v-card-title class="text-subtitle-1">
          <v-icon start size="small">mdi-information</v-icon>
          Basic Information
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="editableScope.display_name"
            label="Display Name"
            :disabled="saving || !canEditSettings"
            @update:model-value="markDirty"
          />
          <v-textarea
            v-model="editableScope.description"
            label="Description"
            rows="3"
            :disabled="saving || !canEditSettings"
            @update:model-value="markDirty"
          />
          <v-text-field
            v-model="editableScope.institution"
            label="Institution"
            :disabled="saving || !canEditSettings"
            @update:model-value="markDirty"
          />
          <v-switch
            v-model="editableScope.is_public"
            label="Public Scope"
            hint="Public scopes are visible to all users"
            persistent-hint
            :disabled="saving || !canEditSettings"
            @update:model-value="markDirty"
          />
        </v-card-text>
      </v-card>

      <!-- Save Button -->
      <div v-if="canEditSettings" class="d-flex justify-end">
        <v-btn color="primary" :loading="saving" :disabled="!isDirty" @click="saveSettings">
          <v-icon start>mdi-content-save</v-icon>
          Save Settings
        </v-btn>
      </div>

      <!-- Read-only message for non-admins -->
      <v-alert v-if="!canEditSettings" type="info" variant="tonal" class="mt-4">
        <template #prepend>
          <v-icon>mdi-lock</v-icon>
        </template>
        Only scope administrators can modify these settings.
      </v-alert>
    </v-card-text>

    <!-- Success/Error Snackbar -->
    <v-snackbar v-model="showSnackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
      <template #actions>
        <v-btn variant="text" @click="showSnackbar = false">Close</v-btn>
      </template>
    </v-snackbar>
  </v-card>
</template>

<script setup>
  import { ref, computed, onMounted, watch } from 'vue'
  import { scopesAPI } from '@/api/scopes'
  import { schemasAPI } from '@/api/schemas'
  import { useAuthStore } from '@/stores/auth'
  import { logService } from '@/services/logService'

  const props = defineProps({
    scope: {
      type: Object,
      required: true
    }
  })

  const emit = defineEmits(['updated'])

  const authStore = useAuthStore()

  // State
  const loadingWorkflowPairs = ref(false)
  const saving = ref(false)
  const isDirty = ref(false)
  const workflowPairs = ref([])
  const selectedWorkflowPairId = ref(null)
  const editableScope = ref({
    display_name: '',
    description: '',
    institution: '',
    is_public: false
  })

  // Snackbar
  const showSnackbar = ref(false)
  const snackbarMessage = ref('')
  const snackbarColor = ref('success')

  // Computed
  const canEditSettings = computed(() => {
    // Admin users or scope admins can edit
    return authStore.isAdmin || authStore.user?.role === 'admin'
  })

  const selectedWorkflowPair = computed(() => {
    return workflowPairs.value.find(wp => wp.id === selectedWorkflowPairId.value)
  })

  // Methods
  function markDirty() {
    isDirty.value = true
  }

  async function loadWorkflowPairs() {
    loadingWorkflowPairs.value = true
    try {
      const pairs = await schemasAPI.getWorkflowPairs({ active_only: true })
      workflowPairs.value = pairs.map(pair => ({
        ...pair,
        displayName: `${pair.name} (${pair.version})`
      }))
    } catch (error) {
      logService.error('Failed to load workflow pairs', { error: error.message })
      showError('Failed to load workflow pairs')
    } finally {
      loadingWorkflowPairs.value = false
    }
  }

  function handleWorkflowPairChange() {
    isDirty.value = true
  }

  async function saveSettings() {
    saving.value = true
    try {
      const updateData = {
        display_name: editableScope.value.display_name,
        description: editableScope.value.description,
        institution: editableScope.value.institution,
        is_public: editableScope.value.is_public,
        default_workflow_pair_id: selectedWorkflowPairId.value
      }

      await scopesAPI.updateScope(props.scope.id, updateData)

      isDirty.value = false
      showSuccess('Settings saved successfully')
      emit('updated')

      logService.info('Scope settings updated', {
        scope_id: props.scope.id,
        workflow_pair_id: selectedWorkflowPairId.value
      })
    } catch (error) {
      logService.error('Failed to save scope settings', { error: error.message })
      showError(`Failed to save settings: ${error.message}`)
    } finally {
      saving.value = false
    }
  }

  function showSuccess(message) {
    snackbarMessage.value = message
    snackbarColor.value = 'success'
    showSnackbar.value = true
  }

  function showError(message) {
    snackbarMessage.value = message
    snackbarColor.value = 'error'
    showSnackbar.value = true
  }

  function initializeFromScope() {
    editableScope.value = {
      display_name: props.scope.display_name || '',
      description: props.scope.description || '',
      institution: props.scope.institution || '',
      is_public: props.scope.is_public || false
    }
    selectedWorkflowPairId.value = props.scope.default_workflow_pair_id || null
    isDirty.value = false
  }

  // Watch for scope prop changes
  watch(
    () => props.scope,
    () => {
      initializeFromScope()
    },
    { deep: true }
  )

  // Lifecycle
  onMounted(async () => {
    initializeFromScope()
    await loadWorkflowPairs()
  })
</script>
