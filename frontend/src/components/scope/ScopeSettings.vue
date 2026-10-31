<!--
  Scope Settings Component

  Configures scope-level settings including workflow pair selection.
  Per ClinGen SOP v11, the scope defines the methodology (workflow pair)
  that ALL genes in the scope follow.
-->

<template>
  <v-card variant="flat" border>
    <v-card-text>
      <h2 class="text-title-medium mb-3">Workflow</h2>
      <p v-if="!scope.default_workflow_pair_id" class="text-body-medium text-warning mb-3">
        No workflow configured. Select a workflow pair to enable precuration and curation for genes
        in this scope.
      </p>

      <v-select
        v-model="selectedWorkflowPairId"
        :items="workflowPairs"
        item-title="displayName"
        item-value="id"
        label="Workflow pair"
        hint="Defines the precuration and curation schemas for all genes in this scope"
        persistent-hint
        :loading="loadingWorkflowPairs"
        :disabled="saving || !canEditSettings"
        clearable
        @update:model-value="handleWorkflowPairChange"
      >
        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps">
            <template #subtitle> {{ item.version }} • {{ item.description }} </template>
          </v-list-item>
        </template>
        <template #selection="{ item }"> {{ item.name }} ({{ item.version }}) </template>
      </v-select>

      <v-select
        v-model="allowedPairIds"
        :items="selectablePairs"
        item-title="displayName"
        item-value="id"
        label="Other allowed workflows"
        hint="Curators may pick these instead of the default; none selected allows the default only"
        persistent-hint
        multiple
        chips
        closable-chips
        :loading="loadingWorkflowPairs"
        :disabled="saving || !canEditSettings"
        class="mt-4"
        data-testid="allowed-workflow-pairs"
        @update:model-value="markDirty"
      />

      <ul v-if="selectedWorkflowPair" class="text-body-medium mt-3 ml-4">
        <li>
          Precuration schema:
          {{ selectedWorkflowPair.precuration_schema_name || 'Not configured' }}
        </li>
        <li>
          Curation schema: {{ selectedWorkflowPair.curation_schema_name || 'Not configured' }}
        </li>
      </ul>

      <h2 class="text-title-medium mt-6 mb-3">Basic information</h2>
      <v-text-field
        v-model="editableScope.display_name"
        label="Display name"
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
        label="Public scope"
        hint="Public scopes are visible to all users"
        persistent-hint
        :disabled="saving || !canEditSettings"
        @update:model-value="markDirty"
      />
      <v-switch
        v-model="editableScope.approvals_require_session"
        label="Approvals need a signed-in person"
        hint="Agent tokens and MCP can comment and request changes, but not approve"
        persistent-hint
        :disabled="saving || !canEditSettings"
        @update:model-value="markDirty"
      />
      <v-switch
        v-model="editableScope.export_evidence_public"
        label="Export evidence publicly"
        hint="Anyone can export this public scope's evidence as stored, including curator free text (rationales, notes)"
        persistent-hint
        :disabled="saving || !canEditSettings"
        @update:model-value="markDirty"
      />

      <div v-if="canEditSettings" class="d-flex align-center justify-end ga-3 mt-4">
        <span v-if="!isDirty" class="text-body-small text-medium-emphasis">No changes to save</span>
        <v-btn
          color="primary"
          variant="flat"
          :loading="saving"
          :disabled="!isDirty"
          @click="saveSettings"
        >
          Save settings
        </v-btn>
      </div>

      <!-- Application admins and the scope creator only -->
      <section v-if="canDeleteScope" class="delete-zone mt-6 pa-4">
        <h2 class="text-title-medium mb-2">Delete this scope</h2>
        <p class="text-body-medium mb-3">
          <template v-if="hasActiveAssignments">
            This scope has {{ activeGeneCount }} active gene assignment{{
              activeGeneCount !== 1 ? 's' : ''
            }}. Deleting removes them with all precurations, curations and reviews.
          </template>
          <template v-else>
            Deleting this scope is permanent and removes all its memberships.
          </template>
        </p>
        <v-btn color="error" variant="outlined" :loading="deleting" @click="openDeleteDialog">
          Delete {{ scopeLabel }}
        </v-btn>
      </section>
    </v-card-text>

    <BaseDialog
      v-model="showDeleteDialog"
      persistent
      size="md"
      :title="`Delete ${scopeLabel}?`"
      @cancel="!deleting && (showDeleteDialog = false)"
    >
      <p class="mb-3">
        <template v-if="hasActiveAssignments">
          {{ activeGeneCount }} gene assignment{{ activeGeneCount !== 1 ? 's' : '' }} will be
          permanently deleted with all precurations, curations and reviews.
        </template>
        <template v-else>This cannot be undone. All scope memberships will be removed.</template>
        To confirm, type <strong>{{ scopeLabel }}</strong
        >.
      </p>
      <v-text-field
        v-model="typedName"
        :label="`Type ${scopeLabel}`"
        autofocus
        hide-details
        autocomplete="off"
      />
      <template #actions>
        <v-btn variant="text" :disabled="deleting" @click="showDeleteDialog = false">Cancel</v-btn>
        <v-btn
          color="error"
          variant="flat"
          :loading="deleting"
          :disabled="typedName !== scopeLabel"
          @click="deleteScope"
        >
          Delete {{ scopeLabel }}
        </v-btn>
      </template>
    </BaseDialog>
  </v-card>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue'
  import { isAxiosError } from 'axios'
  import { onBeforeRouteLeave } from 'vue-router'
  import { useConfirm } from '@/composables/useConfirm'
  import { scopesAPI } from '@/api/scopes'
  import { useAuthStore } from '@/stores/auth'
  import { useScopesStore } from '@/stores/scopes'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { logService } from '@/services/logService'
  import { useWorkflowPairs } from './useWorkflowPairs'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { showError, showSuccess } from '@/composables/useNotifications'

  /** Scope fields this panel reads and edits */
  interface SettingsScope {
    id: string
    name: string
    display_name?: string | null
    description?: string | null
    institution?: string | null
    is_public?: boolean | null
    approvals_require_session?: boolean | null
    export_evidence_public?: boolean | null
    created_by?: string | null
    default_workflow_pair_id?: string | null
    allowed_workflow_pair_ids?: string[] | null
  }

  /** Only the counter used for the delete warning */
  interface SettingsStatistics {
    total_genes_assigned?: number
  }

  const props = withDefaults(
    defineProps<{
      scope: SettingsScope
      statistics?: SettingsStatistics | null
    }>(),
    {
      statistics: null
    }
  )

  const emit = defineEmits<{
    updated: []
    deleted: []
  }>()

  const authStore = useAuthStore()
  const scopeStore = useScopesStore()
  const { canManageScope } = useScopePermissions(computed(() => scopeStore.currentUserRole))

  // State
  const saving = ref(false)
  const deleting = ref(false)
  const showDeleteDialog = ref(false)
  const typedName = ref('')
  const isDirty = ref(false)
  const selectedWorkflowPairId = ref<string | null>(null)
  const allowedPairIds = ref<string[]>([])
  const editableScope = ref({
    display_name: '',
    description: '',
    institution: '',
    is_public: false,
    approvals_require_session: false,
    export_evidence_public: false
  })

  const {
    workflowPairs,
    loading: loadingWorkflowPairs,
    loadWorkflowPairs
  } = useWorkflowPairs(showError)

  // Computed
  const canEditSettings = computed(() => authStore.isAdmin || canManageScope.value)

  // Only platform admins delete scopes (the API and RLS allow nobody else, #284)
  const canDeleteScope = computed(() => authStore.isAdmin)

  const activeGeneCount = computed(() => {
    // Use total_genes_assigned from statistics (this counts active assignments)
    return props.statistics?.total_genes_assigned || 0
  })

  const hasActiveAssignments = computed(() => {
    return activeGeneCount.value > 0
  })

  // Global pairs and this scope's own, besides the default (#284)
  const selectablePairs = computed(() =>
    workflowPairs.value.filter(
      wp =>
        wp.id !== selectedWorkflowPairId.value &&
        (!wp.owner_scope_id || wp.owner_scope_id === props.scope.id)
    )
  )

  const selectedWorkflowPair = computed(() => {
    return workflowPairs.value.find(wp => wp.id === selectedWorkflowPairId.value)
  })

  const scopeLabel = computed(() => props.scope.display_name || props.scope.name)

  // Methods
  function markDirty() {
    isDirty.value = true
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
        approvals_require_session: editableScope.value.approvals_require_session,
        export_evidence_public: editableScope.value.export_evidence_public,
        default_workflow_pair_id: selectedWorkflowPairId.value
      }

      await scopesAPI.updateScope(props.scope.id, updateData)
      const allowed = allowedPairIds.value.filter(id => id !== selectedWorkflowPairId.value)
      if (allowed.join() !== (props.scope.allowed_workflow_pair_ids ?? []).join()) {
        await scopesAPI.setAllowedWorkflowPairs(props.scope.id, allowed)
      }

      isDirty.value = false
      showSuccess('Settings saved successfully')
      emit('updated')

      logService.info('Scope settings updated', {
        scope_id: props.scope.id,
        workflow_pair_id: selectedWorkflowPairId.value
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : undefined
      logService.error('Failed to save scope settings', { error: message })
      showError(`Failed to save settings: ${message}`)
    } finally {
      saving.value = false
    }
  }

  function openDeleteDialog() {
    typedName.value = ''
    showDeleteDialog.value = true
  }

  async function deleteScope() {
    deleting.value = true
    try {
      // Use force=true if there are active assignments
      await scopesAPI.deleteScope(props.scope.id, { force: hasActiveAssignments.value })

      logService.info('Scope deleted', {
        scope_id: props.scope.id,
        had_assignments: hasActiveAssignments.value,
        assignment_count: activeGeneCount.value
      })
      showDeleteDialog.value = false
      isDirty.value = false // scope is gone; leaving must not prompt
      emit('deleted')
    } catch (error) {
      const fallback = error instanceof Error ? error.message : undefined
      logService.error('Failed to delete scope', { error: fallback })
      const detail = isAxiosError<{ detail?: string }>(error)
        ? error.response?.data?.detail
        : undefined
      showError(`Failed to delete scope: ${detail || fallback}`)
    } finally {
      deleting.value = false
    }
  }

  function initializeFromScope() {
    editableScope.value = {
      display_name: props.scope.display_name || '',
      description: props.scope.description || '',
      institution: props.scope.institution || '',
      is_public: props.scope.is_public || false,
      approvals_require_session: props.scope.approvals_require_session || false,
      export_evidence_public: props.scope.export_evidence_public || false
    }
    selectedWorkflowPairId.value = props.scope.default_workflow_pair_id || null
    allowedPairIds.value = [...(props.scope.allowed_workflow_pair_ids ?? [])]
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

  // Leaving the settings route with edits would silently drop them. The tab switch lives in
  // ScopeDashboard and needs the same check (follow-up).
  const { confirm } = useConfirm()
  onBeforeRouteLeave(
    async () =>
      !isDirty.value ||
      confirm({
        title: 'Discard unsaved changes?',
        text: 'Your edits to the scope settings have not been saved.',
        confirmText: 'Discard',
        destructive: true
      })
  )

  // Lifecycle
  onMounted(async () => {
    initializeFromScope()
    await loadWorkflowPairs()
  })
</script>

<style scoped>
  .delete-zone {
    border: 1px solid rgb(var(--v-theme-error));
    border-radius: 4px;
  }
</style>
