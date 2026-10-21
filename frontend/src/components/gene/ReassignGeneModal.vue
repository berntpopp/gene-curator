<!--
  ReassignGeneModal Component

  Modal dialog for reassigning a gene to a different curator within a scope.
  Purpose-built for single gene reassignment with a streamlined UX.

  **Features**:
  - Displays current gene info (read-only)
  - Shows current curator assignment
  - Allows selecting a new curator

  **Props**:
  - modelValue: v-model for dialog visibility
  - scopeId: Required scope UUID
  - gene: Gene object with assignment info

  **Events**:
  - update:modelValue: Dialog visibility change
  - reassigned: Emitted when reassignment is successful

  @example
  <ReassignGeneModal
    v-model="showModal"
    :scope-id="scopeId"
    :gene="selectedGene"
    @reassigned="handleReassigned"
  />
-->

<template>
  <v-dialog v-model="isOpen" max-width="550" persistent @keydown.escape="handleCancel">
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start color="primary" size="28">mdi-account-switch</v-icon>
        <span class="text-h6">Reassign Gene</span>
        <v-spacer />
        <v-btn
          aria-label="Close"
          icon="mdi-close"
          variant="text"
          density="compact"
          @click="handleCancel"
        />
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
        <!-- Gene Info (Read-only) -->
        <v-card variant="tonal" color="primary" class="mb-4">
          <v-card-text class="py-3">
            <div class="d-flex align-center">
              <v-icon color="primary" class="mr-3">mdi-dna</v-icon>
              <div>
                <div class="text-subtitle-1 font-weight-bold">{{ gene?.gene_symbol }}</div>
                <div v-if="gene?.gene_hgnc_id" class="text-caption text-medium-emphasis">
                  {{ gene.gene_hgnc_id }}
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <!-- Current Curator -->
        <div class="mb-4">
          <div class="text-subtitle-2 text-medium-emphasis mb-2">Current Curator</div>
          <v-chip v-if="gene?.curator_name" color="grey" variant="tonal" size="default">
            <v-icon start size="small">mdi-account</v-icon>
            {{ gene.curator_name }}
          </v-chip>
          <v-chip v-else variant="outlined" size="default">
            <v-icon start size="small">mdi-account-off</v-icon>
            Unassigned
          </v-chip>
        </div>

        <v-divider class="mb-4" />

        <!-- New Curator Selection -->
        <v-form ref="formRef" v-model="formValid">
          <div class="text-subtitle-2 mb-2">
            <v-icon start size="small" color="primary">mdi-account-arrow-right</v-icon>
            Reassign to
          </div>

          <v-autocomplete
            v-model="selectedCurator"
            :items="availableCurators"
            :loading="loadingCurators"
            item-title="displayName"
            item-value="user_id"
            label="Select new curator"
            placeholder="Search for a curator..."
            prepend-inner-icon="mdi-account"
            variant="outlined"
            :rules="[v => !!v || 'Please select a curator']"
            :no-data-text="loadingCurators ? 'Loading curators...' : 'No curators available'"
            return-object
            density="comfortable"
            class="mb-3"
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
                <template #append>
                  <v-chip
                    v-if="item.user_id === gene?.curator_id"
                    size="x-small"
                    color="grey"
                    variant="outlined"
                  >
                    Current
                  </v-chip>
                </template>
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
        </v-form>

        <!-- Reassignment Preview -->
        <v-expand-transition>
          <v-alert
            v-if="selectedCurator && selectedCurator.user_id !== gene?.curator_id"
            type="success"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <div class="d-flex align-center">
              <v-icon start size="small">mdi-arrow-right</v-icon>
              <span>
                <strong>{{ gene?.gene_symbol }}</strong> will be reassigned to
                <strong>{{ selectedCurator.full_name || selectedCurator.email }}</strong>
              </span>
            </div>
          </v-alert>
        </v-expand-transition>

        <!-- Same Curator Warning -->
        <v-expand-transition>
          <v-alert
            v-if="selectedCurator && selectedCurator.user_id === gene?.curator_id"
            type="warning"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <div class="d-flex align-center">
              <v-icon start size="small">mdi-alert</v-icon>
              <span>This gene is already assigned to this curator</span>
            </div>
          </v-alert>
        </v-expand-transition>
      </v-card-text>

      <v-divider />

      <!-- Actions -->
      <v-card-actions class="pa-4">
        <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!canSubmit"
          :loading="isReassigning"
          @click="handleSubmit"
        >
          <v-icon start>mdi-account-switch</v-icon>
          Reassign
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import { ref, computed, watch } from 'vue'
  import { assignmentsAPI } from '@/api'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import type { ApiErrorLike } from '@/components/forms/types'
  import type { CuratorOption, GeneRow } from './types'
  import { getAvatarColor, getInitials, toCuratorOption } from './curatorDisplay'

  // ============================================
  // PROPS & EMITS
  // ============================================

  const props = withDefaults(
    defineProps<{
      modelValue?: boolean
      scopeId: string
      gene?: GeneRow | null
    }>(),
    {
      modelValue: false,
      gene: null
    }
  )

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    reassigned: []
  }>()

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
  const loadingCurators = ref(false)
  const isReassigning = ref(false)

  // Data
  const availableCurators = ref<CuratorOption[]>([])

  // Form state
  const selectedCurator = ref<CuratorOption | null>(null)

  // ============================================
  // COMPUTED
  // ============================================

  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  const canSubmit = computed(() => {
    return (
      selectedCurator.value &&
      selectedCurator.value.user_id !== props.gene?.curator_id &&
      props.gene?.assignment_id
    )
  })

  // ============================================
  // METHODS
  // ============================================

  /**
   * Fetch available curators for the scope
   */
  const fetchAvailableCurators = async () => {
    loadingCurators.value = true
    try {
      const members = await scopesStore.fetchMembers(props.scopeId)

      // Reviewers must not curate (four-eyes principle)
      availableCurators.value = members
        .filter(m => ['curator', 'admin'].includes(m.role))
        .map(toCuratorOption)

      logger.debug('Available curators loaded for reassignment', {
        count: availableCurators.value.length
      })
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
    selectedCurator.value = null
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
    if (!canSubmit.value || !props.gene || !selectedCurator.value) return

    // Validate form
    const { valid } = await formRef.value!.validate()
    if (!valid) return

    isReassigning.value = true

    try {
      // Use the assignCurator endpoint to reassign
      await assignmentsAPI.assignCurator(props.gene.assignment_id, selectedCurator.value.user_id)

      logger.info('Gene reassigned successfully', {
        gene_id: props.gene.gene_id,
        gene_symbol: props.gene.gene_symbol,
        new_curator_id: selectedCurator.value.user_id,
        previous_curator_id: props.gene.curator_id
      })

      notificationStore.addToast(
        `${props.gene.gene_symbol} reassigned to ${selectedCurator.value.full_name || selectedCurator.value.email}`,
        'success'
      )

      emit('reassigned')
      resetForm()
      isOpen.value = false
    } catch (error) {
      const apiError = error as ApiErrorLike
      logger.error('Failed to reassign gene', { error: apiError.message })
      notificationStore.addToast(
        `Failed to reassign: ${(apiError.response as { data?: { detail?: string } } | undefined)?.data?.detail || apiError.message}`,
        'error'
      )
    } finally {
      isReassigning.value = false
    }
  }

  // ============================================
  // WATCHERS
  // ============================================

  // Load data when dialog opens
  watch(isOpen, async newValue => {
    if (newValue && props.gene) {
      logger.debug('ReassignGeneModal opened', { gene_symbol: props.gene.gene_symbol })
      await fetchAvailableCurators()
    } else {
      resetForm()
    }
  })
</script>

<style scoped>
  .text-subtitle-2 {
    display: flex;
    align-items: center;
  }
</style>
