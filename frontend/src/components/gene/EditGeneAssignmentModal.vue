<!--
  EditGeneAssignmentModal Component

  Modal dialog for editing gene assignment details within a scope.
  Allows editing priority, due date and notes.

  **Features**:
  - Displays current gene info (read-only)
  - Priority level selection (high, medium, low)
  - Due date picker with calendar
  - Assignment notes textarea

  **Props**:
  - modelValue: v-model for dialog visibility
  - scopeId: Required scope UUID
  - gene: Gene assignment object with current values

  **Events**:
  - update:modelValue: Dialog visibility change
  - updated: Emitted when assignment is successfully updated

  @example
  <EditGeneAssignmentModal
    v-model="showModal"
    :scope-id="scopeId"
    :gene="selectedGene"
    @updated="handleUpdated"
  />
-->

<template>
  <BaseDialog v-model="isOpen" persistent size="md" @cancel="handleCancel">
    <template #title
      ><v-icon start color="primary" size="28">mdi-pencil</v-icon>
      <span class="text-title-large">Edit Gene Assignment</span>
      <v-spacer />
      <v-btn
        aria-label="Close"
        icon="mdi-close"
        variant="text"
        density="compact"
        @click="handleCancel"
    /></template>
    <v-card variant="tonal" color="primary" class="mb-4">
      <v-card-text class="py-3">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon color="primary" class="mr-3">mdi-dna</v-icon>
            <div>
              <div class="text-body-large font-weight-bold">{{ gene?.gene_symbol }}</div>
              <div v-if="gene?.gene_hgnc_id" class="text-body-small text-medium-emphasis">
                {{ gene.gene_hgnc_id }}
              </div>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Edit Form -->
    <v-form ref="formRef" v-model="formValid">
      <!-- Priority Selection -->
      <div class="mb-4">
        <div class="text-title-small mb-2">
          <v-icon start size="small" color="primary">mdi-flag</v-icon>
          Priority Level
        </div>
        <v-btn-toggle v-model="formData.priority" mandatory color="primary" variant="outlined">
          <v-btn
            v-for="option in priorityOptions"
            :key="option.value"
            :value="option.value"
            size="small"
          >
            <v-icon start size="small" :color="getPriorityColor(option.value)">mdi-flag</v-icon>
            {{ option.title }}
          </v-btn>
        </v-btn-toggle>
      </div>

      <!-- Due Date Picker -->
      <div class="mb-4">
        <v-text-field
          v-model="formData.due_date"
          type="date"
          label="Due date"
          variant="outlined"
          density="compact"
          clearable
          hint="Optional deadline for this assignment"
          persistent-hint
        />
      </div>

      <!-- Assignment Notes -->
      <div>
        <div class="text-title-small mb-2">
          <v-icon start size="small" color="primary">mdi-note-text</v-icon>
          Assignment Notes
        </div>
        <v-textarea
          v-model="formData.assignment_notes"
          variant="outlined"
          density="compact"
          rows="3"
          counter="1000"
          placeholder="Add notes about this gene assignment..."
          :rules="[v => !v || v.length <= 1000 || 'Max 1000 characters']"
        />
      </div>
    </v-form>

    <!-- Change Preview -->
    <v-expand-transition>
      <v-alert v-if="hasChanges" type="info" variant="tonal" density="compact" class="mt-3">
        <div class="d-flex align-center">
          <v-icon start size="small">mdi-information</v-icon>
          <span>You have unsaved changes</span>
        </div>
      </v-alert>
    </v-expand-transition>
    <template #actions>
      <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :disabled="!hasChanges"
        :loading="isSaving"
        @click="handleSubmit"
      >
        <v-icon start>mdi-content-save</v-icon>
        Save changes
      </v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  import { ref, computed, watch } from 'vue'
  import { assignmentsAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'
  import type { ApiErrorLike } from '@/components/forms/types'
  import { getPriorityColor, priorityOptions } from '@/components/dynamic/assignmentDisplay'
  import type { GeneRow } from './types'
  import BaseDialog from '@/components/BaseDialog.vue'

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
    updated: []
  }>()

  type Priority = 'low' | 'medium' | 'high'

  interface AssignmentForm {
    priority: Priority
    due_date: string | null
    assignment_notes: string
  }

  // ============================================
  // COMPOSABLES & STORES
  // ============================================

  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // ============================================
  // STATE
  // ============================================

  // Form ref (bound in template as ref="formRef")
  const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const formValid = ref(false)

  // Loading states
  const isSaving = ref(false)

  // Form data
  const formData = ref<AssignmentForm>({
    priority: 'medium',
    due_date: null,
    assignment_notes: ''
  })

  // Original data for change detection
  const originalData = ref<Partial<AssignmentForm>>({})

  // ============================================
  // COMPUTED
  // ============================================

  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  const hasChanges = computed(() => {
    return (
      formData.value.priority !== originalData.value.priority ||
      formData.value.due_date !== originalData.value.due_date ||
      formData.value.assignment_notes !== originalData.value.assignment_notes
    )
  })

  // ============================================
  // METHODS
  // ============================================

  /**
   * Format date for input field (YYYY-MM-DD)
   */
  const formatDateForInput = (date: string | Date | null | undefined): string | null => {
    if (!date) return null
    if (typeof date === 'string') {
      // If it's already a string, try to parse and format
      const d = new Date(date)
      if (isNaN(d.getTime())) return null
      return d.toISOString().split('T')[0] ?? null
    }
    return date.toISOString().split('T')[0] ?? null
  }

  /**
   * Initialize form data from gene prop
   */
  const initializeForm = () => {
    if (props.gene) {
      const priority = (props.gene.priority || 'medium') as Priority
      const dueDate = formatDateForInput(props.gene.due_date)
      const notes = props.gene.assignment_notes || ''

      formData.value = {
        priority,
        due_date: dueDate,
        assignment_notes: notes
      }

      // Store original for change detection
      originalData.value = {
        priority,
        due_date: dueDate,
        assignment_notes: notes
      }
    }
  }

  /**
   * Reset form state
   */
  const resetForm = () => {
    formData.value = {
      priority: 'medium',
      due_date: null,
      assignment_notes: ''
    }
    originalData.value = {}
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
    if (!hasChanges.value || !props.gene?.assignment_id) return

    // Validate form
    const { valid } = await formRef.value!.validate()
    if (!valid) return

    isSaving.value = true

    try {
      // Send only edited fields: list rows may lack due_date/notes, and resending the
      // blank form values would erase what the server has stored
      const form = formData.value
      const original = originalData.value
      const updateData: {
        priority_level?: Priority
        assignment_notes?: string | null
        due_date?: string | null
      } = {}
      if (form.priority !== original.priority) {
        updateData.priority_level = form.priority
      }
      if (form.assignment_notes !== original.assignment_notes) {
        updateData.assignment_notes = form.assignment_notes || null
      }
      if (form.due_date !== original.due_date) {
        updateData.due_date = form.due_date ? new Date(form.due_date).toISOString() : null
      }

      await assignmentsAPI.updateAssignment(props.gene.assignment_id, updateData)

      logger.info('Gene assignment updated', {
        assignment_id: props.gene.assignment_id,
        gene_symbol: props.gene.gene_symbol,
        changes: {
          priority: formData.value.priority,
          due_date: formData.value.due_date,
          has_notes: !!formData.value.assignment_notes
        }
      })

      notificationStore.addToast(`${props.gene.gene_symbol} assignment updated`, 'success')

      emit('updated')
      resetForm()
      isOpen.value = false
    } catch (error) {
      const apiError = error as ApiErrorLike
      logger.error('Failed to update assignment', { error: apiError.message })
      notificationStore.addToast(
        `Failed to update: ${(apiError.response as { data?: { detail?: string } } | undefined)?.data?.detail || apiError.message}`,
        'error'
      )
    } finally {
      isSaving.value = false
    }
  }

  // ============================================
  // WATCHERS
  // ============================================

  // Initialize form when dialog opens
  watch(isOpen, newValue => {
    if (newValue && props.gene) {
      logger.debug('EditGeneAssignmentModal opened', { gene_symbol: props.gene.gene_symbol })
      initializeForm()
    } else {
      resetForm()
    }
  })
</script>
<style scoped>
  .text-title-small {
    display: flex;
    align-items: center;
  }
</style>
