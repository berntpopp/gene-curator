<!--
  AssignCuratorModal Component

  Modal dialog for assigning genes to curators within a scope.
  Replaces the drawer-based approach with a cleaner modal UX.

  **Features**:
  - Multi-gene selection with chips
  - Curator selection with role display
  - Visual preview of assignments
  - Optional due date and priority
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
  <v-dialog v-model="isOpen" max-width="700" persistent @keydown.escape="handleCancel">
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start color="primary" size="28">mdi-account-arrow-right</v-icon>
        <span class="text-h6">Assign Genes to Curator</span>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" density="compact" @click="handleCancel" />
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
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
            :no-data-text="loadingGenes ? 'Loading genes...' : 'No unassigned genes available'"
            return-object
            density="comfortable"
            class="mb-4"
          >
            <template #chip="{ item, props: chipProps }">
              <v-chip v-bind="chipProps" color="primary" variant="tonal" size="small">
                <v-icon start size="x-small">mdi-dna</v-icon>
                {{ item.raw.approved_symbol }}
              </v-chip>
            </template>

            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps" :title="undefined">
                <template #prepend>
                  <v-checkbox-btn :model-value="isGeneSelected(item.raw)" />
                </template>
                <v-list-item-title class="font-weight-medium">
                  {{ item.raw.approved_symbol }}
                </v-list-item-title>
                <v-list-item-subtitle v-if="item.raw.hgnc_id" class="text-caption">
                  {{ item.raw.hgnc_id }}
                  <span v-if="item.raw.approved_name" class="mx-1">|</span>
                  {{ item.raw.approved_name }}
                </v-list-item-subtitle>
              </v-list-item>
            </template>

            <template #prepend-item>
              <v-list-item @click="toggleSelectAll">
                <template #prepend>
                  <v-checkbox-btn
                    :model-value="allGenesSelected"
                    :indeterminate="someGenesSelected"
                  />
                </template>
                <v-list-item-title class="font-weight-medium">
                  {{ allGenesSelected ? 'Deselect All' : 'Select All' }}
                </v-list-item-title>
              </v-list-item>
              <v-divider />
            </template>
          </v-autocomplete>

          <!-- Selected genes summary -->
          <v-expand-transition>
            <v-alert
              v-if="selectedGenes.length > 0"
              type="info"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              <div class="d-flex align-center">
                <v-icon start size="small">mdi-information</v-icon>
                <span>{{ selectedGenes.length }} gene(s) selected for assignment</span>
              </div>
            </v-alert>
          </v-expand-transition>

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
                  <v-avatar size="36" :color="getAvatarColor(item.raw.email)">
                    <span class="text-body-2 font-weight-bold text-white">
                      {{ getInitials(item.raw.full_name || item.raw.email) }}
                    </span>
                  </v-avatar>
                </template>
                <v-list-item-title>
                  {{ item.raw.full_name || item.raw.email }}
                </v-list-item-title>
                <v-list-item-subtitle class="d-flex align-center">
                  <v-chip :color="getRoleColor(item.raw.role)" size="x-small" class="mr-2">
                    {{ item.raw.role }}
                  </v-chip>
                  <span class="text-caption text-medium-emphasis">{{ item.raw.email }}</span>
                </v-list-item-subtitle>
              </v-list-item>
            </template>

            <template #selection="{ item }">
              <div class="d-flex align-center">
                <v-avatar size="24" :color="getAvatarColor(item.raw.email)" class="mr-2">
                  <span class="text-caption font-weight-bold text-white">
                    {{ getInitials(item.raw.full_name || item.raw.email) }}
                  </span>
                </v-avatar>
                <span>{{ item.raw.full_name || item.raw.email }}</span>
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
                    <v-text-field
                      v-model="dueDate"
                      label="Due Date"
                      type="date"
                      variant="outlined"
                      density="compact"
                      hint="Target completion date"
                      persistent-hint
                      clearable
                    />
                  </v-col>
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
                      <template #item="{ item, props: itemProps }">
                        <v-list-item v-bind="itemProps">
                          <template #prepend>
                            <v-icon :color="item.raw.color" size="small">
                              {{ item.raw.icon }}
                            </v-icon>
                          </template>
                        </v-list-item>
                      </template>
                      <template #selection="{ item }">
                        <v-icon :color="item.raw.color" size="small" class="mr-2">
                          {{ item.raw.icon }}
                        </v-icon>
                        {{ item.raw.title }}
                      </template>
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
                <span v-if="dueDate">
                  with due date <strong>{{ formatDate(dueDate) }}</strong></span
                >
                <span v-if="priority !== 'normal'">
                  at <strong>{{ priority }}</strong> priority
                </span>
              </div>
            </v-card>
          </v-expand-transition>
        </v-form>
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
          :loading="isAssigning"
          @click="handleSubmit"
        >
          <v-icon start>mdi-account-check</v-icon>
          Assign {{ selectedGenes.length > 0 ? `(${selectedGenes.length})` : '' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
  import { ref, computed, watch, onMounted } from 'vue'
  import { genesAPI, assignmentsAPI } from '@/api'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'

  // ============================================
  // PROPS & EMITS
  // ============================================

  const props = defineProps({
    modelValue: {
      type: Boolean,
      default: false
    },
    scopeId: {
      type: String,
      required: true
    },
    preSelectedGenes: {
      type: Array,
      default: () => []
    }
  })

  const emit = defineEmits(['update:modelValue', 'assigned'])

  // ============================================
  // COMPOSABLES & STORES
  // ============================================

  const scopesStore = useScopesStore()
  const { getRoleColor: useGetRoleColor } = useRoleColors()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // ============================================
  // STATE
  // ============================================

  const formRef = ref(null)
  const formValid = ref(false)

  // Loading states
  const loadingGenes = ref(false)
  const loadingCurators = ref(false)
  const isAssigning = ref(false)

  // Data
  const availableGenes = ref([])
  const availableCurators = ref([])

  // Form state
  const selectedGenes = ref([])
  const selectedCurator = ref(null)
  const dueDate = ref(null)
  const priority = ref('medium')
  const notes = ref('')

  // Priority options - matches backend: "high" | "medium" | "low"
  const priorityOptions = [
    { title: 'Low', value: 'low', icon: 'mdi-arrow-down', color: 'grey' },
    { title: 'Medium', value: 'medium', icon: 'mdi-minus', color: 'primary' },
    { title: 'High', value: 'high', icon: 'mdi-arrow-up', color: 'warning' }
  ]

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
    return dueDate.value || priority.value !== 'medium' || notes.value
  })

  const optionalSettingsCount = computed(() => {
    let count = 0
    if (dueDate.value) count++
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
  const isGeneSelected = gene => {
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
   * Get avatar color based on email hash
   */
  const getAvatarColor = email => {
    const colors = ['primary', 'secondary', 'success', 'info', 'warning', 'error']
    const hash = (email || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    return colors[hash % colors.length]
  }

  /**
   * Get initials from name
   */
  const getInitials = name => {
    if (!name) return '?'
    const parts = name.trim().split(' ')
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
  }

  /**
   * Get role color
   */
  const getRoleColor = role => {
    return useGetRoleColor(role)
  }

  /**
   * Format date for display
   */
  const formatDate = dateStr => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString()
  }

  /**
   * Fetch available genes for the scope
   */
  const fetchAvailableGenes = async () => {
    loadingGenes.value = true
    try {
      // Fetch genes from catalog (max 500 per backend limit)
      const genesResponse = await genesAPI.getGenes({ limit: 500 })
      const allGenes = genesResponse.genes || genesResponse.items || genesResponse

      // Fetch existing assignments for this scope
      let assignedGeneIds = new Set()
      try {
        const assignments = await assignmentsAPI.getAssignmentsByScope(props.scopeId)
        assignedGeneIds = new Set((assignments || []).map(a => a.gene_id))
      } catch {
        // If no assignments yet, all genes are available
      }

      // Filter to unassigned genes only
      availableGenes.value = allGenes.filter(gene => !assignedGeneIds.has(gene.id))

      logger.debug('Available genes loaded', {
        total: allGenes.length,
        available: availableGenes.value.length
      })
    } catch (error) {
      logger.error('Failed to fetch available genes', { error: error.message })
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

      // Map members with display name
      // API returns user_full_name, user_email from ScopeMembershipResponse
      availableCurators.value = (members || [])
        .filter(m => ['curator', 'scope_admin', 'admin'].includes(m.role))
        .map(member => ({
          ...member,
          // Normalize field names from API response
          full_name: member.user_full_name || member.full_name,
          email: member.user_email || member.email,
          displayName:
            member.user_full_name || member.full_name || member.user_email || member.email
        }))

      logger.debug('Available curators loaded', { count: availableCurators.value.length })
    } catch (error) {
      logger.error('Failed to fetch curators', { error: error.message })
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
    dueDate.value = null
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
    if (!canSubmit.value) return

    // Validate form
    const { valid } = await formRef.value.validate()
    if (!valid) return

    isAssigning.value = true

    try {
      // Create assignments for each selected gene
      // Backend expects assigned_curator_id and priority_level: "high" | "medium" | "low"
      const priorityMapping = {
        low: 'low',
        normal: 'medium',
        medium: 'medium',
        high: 'high',
        urgent: 'high'
      }
      const promises = selectedGenes.value.map(gene =>
        assignmentsAPI.createAssignment({
          gene_id: gene.id,
          scope_id: props.scopeId,
          assigned_curator_id: selectedCurator.value.user_id,
          priority_level: priorityMapping[priority.value] || 'medium',
          assignment_notes: notes.value || undefined
        })
      )

      await Promise.all(promises)

      logger.info('Genes assigned successfully', {
        count: selectedGenes.value.length,
        curator_id: selectedCurator.value.user_id
      })

      notificationStore.addToast(
        `${selectedGenes.value.length} gene(s) assigned to ${selectedCurator.value.full_name || selectedCurator.value.email}`,
        'success'
      )

      emit('assigned')
      resetForm()
      isOpen.value = false
    } catch (error) {
      logger.error('Failed to assign genes', { error: error.message })
      notificationStore.addToast(
        `Failed to assign genes: ${error.response?.data?.detail || error.message}`,
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
