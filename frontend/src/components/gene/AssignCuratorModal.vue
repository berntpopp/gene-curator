<!--
  AssignCuratorModal Component

  Modal dialog for assigning genes to curators within a scope.
  Replaces the drawer-based approach with a cleaner modal UX.

  **Features**:
  - Multi-gene selection with chips
  - Curator selection with role display
  - Visual preview of assignments
  - Optional priority
  - Assignment notes

  **Props**:
  - modelValue: v-model for dialog visibility
  - scopeId: Required scope UUID
  - preSelectedGenes: Optional array of pre-selected gene IDs

  **Events**:
  - update:modelValue: Dialog visibility change
  - assigned: Emitted when assignment is successful

  @example
  <AssignCuratorModal
    v-model="showModal"
    :scope-id="scopeId"
    :pre-selected-genes="selectedGeneIds"
    @assigned="handleAssigned"
  />
-->

<template>
  <BaseDialog v-model="isOpen" persistent size="lg" @cancel="handleCancel">
    <template #title
      ><v-icon start color="primary" size="28">mdi-account-arrow-right</v-icon>
      <span class="text-h6">Assign Genes to Curator</span>
      <v-spacer />
      <v-btn
        aria-label="Close"
        icon="mdi-close"
        variant="text"
        density="compact"
        @click="handleCancel"
    /></template>
    <v-form ref="formRef" v-model="formValid">
      <!-- Step 1: Gene Selection -->
      <div class="section-header mb-2">
        <v-icon start size="small" color="primary">mdi-numeric-1-circle</v-icon>
        <span class="text-subtitle-1 font-weight-medium">Select Genes</span>
      </div>

      <v-autocomplete
        v-model="selectedGenes"
        :items="availableGenes"
        :loading="loadingGenes"
        item-title="approved_symbol"
        item-value="id"
        label="Select genes to assign"
        placeholder="Search or select genes..."
        prepend-inner-icon="mdi-dna"
        variant="outlined"
        multiple
        chips
        closable-chips
        :rules="[v => v?.length > 0 || 'Select at least one gene']"
        :no-data-text="
          loadingGenes ? 'Loading genes...' : 'No genes without a curator in this scope'
        "
        return-object
        density="comfortable"
        class="mb-4"
      >
        <template #chip="{ item, props: chipProps }">
          <v-chip v-bind="chipProps" color="primary" variant="tonal" size="small">
            <v-icon start size="x-small">mdi-dna</v-icon>
            {{ item.approved_symbol }}
          </v-chip>
        </template>

        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps" :title="undefined">
            <template #prepend>
              <v-checkbox-btn :model-value="isGeneSelected(item)" />
            </template>
            <v-list-item-title class="font-weight-medium">
              {{ item.approved_symbol }}
            </v-list-item-title>
            <v-list-item-subtitle v-if="item.hgnc_id" class="text-caption">
              {{ item.hgnc_id }}
            </v-list-item-subtitle>
          </v-list-item>
        </template>

        <template #prepend-item>
          <v-list-item @click="toggleSelectAll">
            <template #prepend>
              <v-checkbox-btn :model-value="allGenesSelected" :indeterminate="someGenesSelected" />
            </template>
            <v-list-item-title class="font-weight-medium">
              {{ allGenesSelected ? 'Deselect All' : 'Select All' }}
            </v-list-item-title>
          </v-list-item>
        </template>
      </v-autocomplete>

      <!-- Step 2: Curator Selection -->
      <div class="section-header mb-2">
        <v-icon start size="small" color="primary">mdi-numeric-2-circle</v-icon>
        <span class="text-subtitle-1 font-weight-medium">Assign to Curator</span>
      </div>

      <v-autocomplete
        v-model="selectedCurator"
        :items="availableCurators"
        :loading="loadingCurators"
        item-title="displayName"
        item-value="user_id"
        label="Select curator"
        placeholder="Search for a curator..."
        prepend-inner-icon="mdi-account"
        variant="outlined"
        :rules="[v => !!v || 'Please select a curator']"
        :no-data-text="loadingCurators ? 'Loading curators...' : 'No curators available'"
        return-object
        density="comfortable"
        class="mb-4"
      >
        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps" :title="undefined">
            <template #prepend>
              <v-avatar size="36" :color="getAvatarColor(item.email)">
                <span class="text-body-2 font-weight-bold text-white">
                  {{ getInitials(item.full_name || item.email) }}
                </span>
              </v-avatar>
            </template>
            <v-list-item-title>
              {{ item.full_name || item.email }}
            </v-list-item-title>
            <v-list-item-subtitle class="d-flex align-center">
              <v-chip :color="getRoleColor(item.role)" size="x-small" class="mr-2">
                {{ item.role }}
              </v-chip>
              <span class="text-caption text-medium-emphasis">{{ item.email }}</span>
            </v-list-item-subtitle>
          </v-list-item>
        </template>

        <template #selection="{ item }">
          <div class="d-flex align-center">
            <v-avatar size="24" :color="getAvatarColor(item.email)" class="mr-2">
              <span class="text-caption font-weight-bold text-white">
                {{ getInitials(item.full_name || item.email) }}
              </span>
            </v-avatar>
            <span>{{ item.full_name || item.email }}</span>
          </div>
        </template>
      </v-autocomplete>

      <!-- Step 3: Optional Settings -->
      <v-expansion-panels variant="accordion" class="mb-2">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small" color="primary">mdi-cog</v-icon>
            <span class="text-subtitle-2">Additional Options</span>
            <template #actions>
              <v-chip v-if="hasOptionalSettings" size="x-small" color="primary" variant="tonal">
                {{ optionalSettingsCount }} set
              </v-chip>
            </template>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row dense>
              <v-col cols="12" sm="6">
                <v-select
                  v-model="priority"
                  :items="priorityOptions"
                  label="Priority"
                  variant="outlined"
                  density="compact"
                  hint="Assignment priority level"
                  persistent-hint
                >
                </v-select>
              </v-col>
              <v-col cols="12">
                <v-textarea
                  v-model="notes"
                  label="Assignment Notes"
                  variant="outlined"
                  density="compact"
                  rows="2"
                  counter="500"
                  placeholder="Add context or instructions for the curator..."
                  :rules="[v => !v || v.length <= 500 || 'Max 500 characters']"
                />
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Assignment Preview -->
      <v-expand-transition>
        <v-card
          v-if="selectedGenes.length > 0 && selectedCurator"
          variant="outlined"
          class="mt-4 pa-3"
          color="success"
        >
          <div class="d-flex align-center mb-2">
            <v-icon color="success" class="mr-2">mdi-check-circle</v-icon>
            <span class="text-subtitle-2">Assignment Preview</span>
          </div>
          <div class="text-body-2">
            <strong>{{ selectedGenes.length }} gene(s)</strong> will be assigned to
            <strong>{{ selectedCurator.full_name || selectedCurator.email }}</strong>
            <span v-if="priority !== 'medium'">
              at <strong>{{ priority }}</strong> priority
            </span>
          </div>
        </v-card>
      </v-expand-transition>
    </v-form>
    <template #actions>
      <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!canSubmit"
        :loading="isAssigning"
        @click="handleSubmit"
      >
        <v-icon start>mdi-account-check</v-icon>
        Assign {{ selectedGenes.length > 0 ? `(${selectedGenes.length})` : '' }}
      </v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  import { ref, computed, watch, onMounted } from 'vue'
  import { assignmentsAPI } from '@/api'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import type { ApiErrorLike } from '@/components/forms/types'
  import { priorityOptions } from '@/components/dynamic/assignmentDisplay'
  import type { CuratorOption } from './types'
  import { getAvatarColor, getInitials, toCuratorOption } from './curatorDisplay'
  import BaseDialog from '@/components/BaseDialog.vue'

  // ============================================
  // PROPS & EMITS
  // ============================================

  const props = withDefaults(
    defineProps<{
      modelValue?: boolean
      scopeId: string
      preSelectedGenes?: string[]
    }>(),
    {
      modelValue: false,
      preSelectedGenes: () => []
    }
  )

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    assigned: []
  }>()

  /** Gene candidate in the assignment picker: a scope gene that has no curator yet. */
  interface GeneCandidate {
    id: string
    approved_symbol: string
    hgnc_id: string
  }

  // ============================================
  // COMPOSABLES & STORES
  // ============================================

  const scopesStore = useScopesStore()
  const { getRoleColor } = useRoleColors()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // ============================================
  // STATE
  // ============================================

  // Form ref (bound in template as ref="formRef")
  const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const formValid = ref(false)

  // Loading states
  const loadingGenes = ref(false)
  const loadingCurators = ref(false)
  const isAssigning = ref(false)

  // Data
  const availableGenes = ref<GeneCandidate[]>([])
  const availableCurators = ref<CuratorOption[]>([])

  // Form state
  const selectedGenes = ref<GeneCandidate[]>([])
  const selectedCurator = ref<CuratorOption | null>(null)
  const priority = ref('medium')
  const notes = ref('')

  // ============================================
  // COMPUTED
  // ============================================

  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  const canSubmit = computed(() => {
    return selectedGenes.value.length > 0 && selectedCurator.value
  })

  const allGenesSelected = computed(() => {
    return (
      availableGenes.value.length > 0 && selectedGenes.value.length === availableGenes.value.length
    )
  })

  const someGenesSelected = computed(() => {
    return selectedGenes.value.length > 0 && !allGenesSelected.value
  })

  const hasOptionalSettings = computed(() => {
    return priority.value !== 'medium' || notes.value
  })

  const optionalSettingsCount = computed(() => {
    let count = 0
    if (priority.value !== 'medium') count++
    if (notes.value) count++
    return count
  })

  // ============================================
  // METHODS
  // ============================================

  /**
   * Check if a gene is currently selected
   */
  const isGeneSelected = (gene: GeneCandidate) => {
    return selectedGenes.value.some(g => g.id === gene.id)
  }

  /**
   * Toggle select all genes
   */
  const toggleSelectAll = () => {
    if (allGenesSelected.value) {
      selectedGenes.value = []
    } else {
      selectedGenes.value = [...availableGenes.value]
    }
  }

  /**
   * Genes already in the scope that have no curator yet
   */
  const fetchAvailableGenes = async () => {
    loadingGenes.value = true
    try {
      const assignments = await assignmentsAPI.getAssignmentsByScope(props.scopeId, {
        limit: 1000
      })
      availableGenes.value = assignments
        .filter(a => a.is_active && !a.assigned_curator_id)
        .map(a => ({ id: a.gene_id, approved_symbol: a.gene_symbol, hgnc_id: a.gene_hgnc_id }))

      logger.debug('Available genes loaded', { available: availableGenes.value.length })
    } catch (error) {
      logger.error('Failed to fetch available genes', { error: (error as ApiErrorLike).message })
      notificationStore.addToast('Failed to load genes', 'error')
    } finally {
      loadingGenes.value = false
    }
  }

  /**
   * Fetch available curators for the scope
   */
  const fetchAvailableCurators = async () => {
    loadingCurators.value = true
    try {
      const members = await scopesStore.fetchMembers(props.scopeId)

      availableCurators.value = members
        .filter(m => ['curator', 'admin'].includes(m.role))
        .map(toCuratorOption)

      logger.debug('Available curators loaded', { count: availableCurators.value.length })
    } catch (error) {
      logger.error('Failed to fetch curators', { error: (error as ApiErrorLike).message })
      notificationStore.addToast('Failed to load curators', 'error')
    } finally {
      loadingCurators.value = false
    }
  }

  /**
   * Reset form state
   */
  const resetForm = () => {
    selectedGenes.value = []
    selectedCurator.value = null
    priority.value = 'medium'
    notes.value = ''
    formValid.value = false
  }

  /**
   * Handle cancel
   */
  const handleCancel = () => {
    resetForm()
    isOpen.value = false
  }

  /**
   * Handle form submission
   */
  const handleSubmit = async () => {
    if (!canSubmit.value || !selectedCurator.value) return

    // Validate form
    const { valid } = await formRef.value!.validate()
    if (!valid) return

    isAssigning.value = true

    try {
      // One request: the backend assigns all genes or none (#191)
      const curatorId = selectedCurator.value.user_id
      const result = await assignmentsAPI.bulkAssignGenes({
        gene_ids: selectedGenes.value.map(gene => gene.id),
        scope_id: props.scopeId,
        assigned_curator_id: curatorId,
        priority_level: priority.value,
        assignment_notes: notes.value || undefined
      })

      logger.info('Genes assigned successfully', {
        count: result.total_created,
        curator_id: curatorId
      })

      const left = selectedGenes.value.length - result.total_created
      const who = selectedCurator.value.full_name || selectedCurator.value.email
      notificationStore.addToast(
        `${result.total_created} gene(s) assigned to ${who}${left > 0 ? ` (${left} skipped)` : ''}`,
        left > 0 ? 'warning' : 'success'
      )

      emit('assigned')
      resetForm()
      isOpen.value = false
    } catch (error) {
      const apiError = error as ApiErrorLike
      logger.error('Failed to assign genes', { error: apiError.message })
      notificationStore.addToast(
        `Failed to assign genes: ${(apiError.response as { data?: { detail?: string } } | undefined)?.data?.detail || apiError.message}`,
        'error'
      )
    } finally {
      isAssigning.value = false
    }
  }

  // ============================================
  // WATCHERS
  // ============================================

  // Load data when dialog opens
  watch(isOpen, async newValue => {
    if (newValue) {
      logger.debug('AssignCuratorModal opened')
      await Promise.all([fetchAvailableGenes(), fetchAvailableCurators()])

      // Pre-select genes if provided
      if (props.preSelectedGenes.length > 0) {
        selectedGenes.value = availableGenes.value.filter(g =>
          props.preSelectedGenes.includes(g.id)
        )
      }
    } else {
      resetForm()
    }
  })

  // Initial load if already open
  onMounted(() => {
    if (props.modelValue) {
      Promise.all([fetchAvailableGenes(), fetchAvailableCurators()])
    }
  })
</script>

<style scoped>
  .section-header {
    display: flex;
    align-items: center;
  }

  .section-header .text-subtitle-1 {
    line-height: 1;
  }
</style>
