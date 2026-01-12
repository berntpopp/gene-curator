<template>
  <v-navigation-drawer
    :model-value="modelValue"
    location="right"
    temporary
    width="500"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <!-- Header -->
    <v-toolbar density="compact" color="primary">
      <v-toolbar-title>Assign Genes to Curators</v-toolbar-title>
      <v-spacer />
      <v-btn icon aria-label="Close" @click="close">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <!-- Content -->
    <v-card-text class="pt-4">
      <v-form ref="formRef">
        <!-- Gene Selection -->
        <div class="text-subtitle-2 mb-2">Select Genes</div>
        <v-autocomplete
          v-model="selectedGenes"
          :items="availableGenes"
          :loading="loadingGenes"
          item-title="gene_symbol"
          item-value="gene_id"
          label="Genes"
          hint="Select one or more genes to assign"
          persistent-hint
          variant="outlined"
          multiple
          chips
          closable-chips
          :rules="[v => (v && v.length > 0) || 'At least one gene is required']"
          class="mb-4"
        >
          <template #chip="{ item, props: chipProps }">
            <v-chip v-bind="chipProps" size="small">
              <v-icon start size="small">mdi-dna</v-icon>
              {{ item.value }}
            </v-chip>
          </template>

          <template #item="{ item, props: itemProps }">
            <v-list-item v-bind="itemProps">
              <template #prepend>
                <v-icon>mdi-dna</v-icon>
              </template>
              <v-list-item-title>{{ item.raw.gene_symbol }}</v-list-item-title>
              <v-list-item-subtitle v-if="item.raw.gene_name">
                {{ item.raw.gene_name }}
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-autocomplete>

        <!-- Curator Selection -->
        <div class="text-subtitle-2 mb-2">Assign to Curator</div>
        <v-autocomplete
          v-model="selectedCurator"
          :items="availableCurators"
          :loading="loadingCurators"
          item-title="full_name"
          item-value="user_id"
          label="Curator"
          hint="Select a curator to assign these genes to"
          persistent-hint
          variant="outlined"
          :rules="[v => !!v || 'Curator is required']"
          class="mb-4"
        >
          <template #item="{ item, props: itemProps }">
            <v-list-item v-bind="itemProps">
              <template #prepend>
                <v-avatar size="32" :color="getAvatarColor(item.raw.email)">
                  <span class="text-uppercase">{{
                    getInitials(item.raw.full_name || item.raw.email)
                  }}</span>
                </v-avatar>
              </template>
              <v-list-item-title>{{ item.raw.full_name || item.raw.email }}</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip size="x-small" :color="getRoleColor(item.raw.role)">
                  {{ item.raw.role }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-autocomplete>

        <!-- Due Date (Optional) -->
        <div class="text-subtitle-2 mb-2">Due Date (Optional)</div>
        <v-text-field
          v-model="dueDate"
          label="Due Date"
          type="date"
          variant="outlined"
          hint="Set a target completion date"
          persistent-hint
          class="mb-4"
        />

        <!-- Priority (Optional) -->
        <div class="text-subtitle-2 mb-2">Priority (Optional)</div>
        <v-select
          v-model="priority"
          :items="priorityOptions"
          label="Priority"
          variant="outlined"
          hint="Set priority level for these assignments"
          persistent-hint
          class="mb-4"
        />

        <!-- Notes (Optional) -->
        <div class="text-subtitle-2 mb-2">Notes (Optional)</div>
        <v-textarea
          v-model="notes"
          label="Assignment Notes"
          hint="Add any additional context for the curator"
          variant="outlined"
          rows="3"
          auto-grow
        />
      </v-form>
    </v-card-text>

    <!-- Actions -->
    <v-card-actions class="px-4 pb-4">
      <v-btn variant="outlined" @click="close">Cancel</v-btn>
      <v-spacer />
      <v-btn color="primary" :loading="assigning" @click="handleAssign">
        <v-icon start>mdi-check</v-icon>
        Assign {{ selectedGenes.length > 0 ? `(${selectedGenes.length})` : '' }}
      </v-btn>
    </v-card-actions>
  </v-navigation-drawer>
</template>

<script setup>
  /**
   * AssignGenesDrawer Component
   *
   * Slide-over drawer for assigning genes to curators within a scope.
   * Follows Week 4 UX pattern: Drawers instead of dialogs for better workflow.
   *
   * Features:
   * - Multi-gene selection with autocomplete
   * - Curator selection with avatar + role display
   * - Optional due date and priority
   * - Assignment notes
   *
   * @example
   * <AssignGenesDrawer
   *   v-model="showDrawer"
   *   :scope-id="scopeId"
   *   @assigned="handleAssigned"
   * />
   */

  import { ref, watch, onMounted } from 'vue'
  import { genesAPI, assignmentsAPI } from '@/api'
  import { useScopesStore } from '@/stores/scopes'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'

  const props = defineProps({
    modelValue: {
      type: Boolean,
      required: true
    },
    scopeId: {
      type: String,
      required: true
    }
  })

  const emit = defineEmits(['update:modelValue', 'assigned'])

  const scopesStore = useScopesStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // Form state
  const formRef = ref(null)
  const selectedGenes = ref([])
  const selectedCurator = ref(null)
  const dueDate = ref(null)
  const priority = ref('normal')
  const notes = ref('')

  // Loading states
  const loadingGenes = ref(false)
  const loadingCurators = ref(false)
  const assigning = ref(false)

  // Data
  const availableGenes = ref([])
  const availableCurators = ref([])

  // Priority options
  const priorityOptions = [
    { title: 'Low', value: 'low' },
    { title: 'Normal', value: 'normal' },
    { title: 'High', value: 'high' },
    { title: 'Urgent', value: 'urgent' }
  ]

  /**
   * Fetch available genes for the scope
   */
  async function fetchAvailableGenes() {
    loadingGenes.value = true
    try {
      // Fetch all genes (would be filtered by scope in real app)
      const allGenes = await genesAPI.getGenes()

      // Fetch already assigned genes
      const assignments = await assignmentsAPI.getAssignments({ scope_id: props.scopeId })
      const assignedGeneIds = new Set(assignments.map(a => a.gene_id))

      // Filter out already assigned genes
      availableGenes.value = allGenes
        .filter(gene => !assignedGeneIds.has(gene.gene_id))
        .map(gene => ({
          gene_id: gene.gene_id,
          gene_symbol: gene.gene_symbol,
          gene_name: gene.gene_name
        }))

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
  async function fetchAvailableCurators() {
    loadingCurators.value = true
    try {
      const members = await scopesStore.fetchMembers(props.scopeId)

      // Filter to only curators and admins
      availableCurators.value = members
        .filter(member => ['curator', 'scope_admin', 'admin'].includes(member.role))
        .map(member => ({
          user_id: member.user_id,
          email: member.email,
          full_name: member.full_name,
          role: member.role
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
   * Get avatar color based on email hash
   */
  function getAvatarColor(email) {
    const colors = ['primary', 'secondary', 'success', 'info', 'warning']
    const hash = email.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    return colors[hash % colors.length]
  }

  /**
   * Get initials from name
   */
  function getInitials(name) {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .substring(0, 2)
  }

  /**
   * Get role color
   */
  function getRoleColor(role) {
    const colors = {
      admin: 'error',
      scope_admin: 'warning',
      curator: 'primary',
      reviewer: 'info',
      viewer: 'grey'
    }
    return colors[role] || 'grey'
  }

  /**
   * Handle assign action
   */
  async function handleAssign() {
    const { valid } = await formRef.value.validate()
    if (!valid) return

    assigning.value = true
    try {
      // Create assignments for each gene
      const assignments = selectedGenes.value.map(geneId => ({
        gene_id: geneId,
        scope_id: props.scopeId,
        curator_id: selectedCurator.value,
        due_date: dueDate.value || null,
        priority: priority.value,
        notes: notes.value || null
      }))

      // Bulk assign
      for (const assignment of assignments) {
        await assignmentsAPI.createAssignment(assignment)
      }

      logger.info('Genes assigned successfully', {
        count: selectedGenes.value.length,
        curator_id: selectedCurator.value
      })

      notificationStore.addToast(
        `${selectedGenes.value.length} gene(s) assigned successfully`,
        'success'
      )

      // Reset form
      resetForm()

      // Emit success event
      emit('assigned')

      // Close drawer
      close()
    } catch (error) {
      logger.error('Failed to assign genes', { error: error.message })
      notificationStore.addToast('Failed to assign genes', 'error')
    } finally {
      assigning.value = false
    }
  }

  /**
   * Reset form
   */
  function resetForm() {
    selectedGenes.value = []
    selectedCurator.value = null
    dueDate.value = null
    priority.value = 'normal'
    notes.value = ''
    if (formRef.value) {
      formRef.value.resetValidation()
    }
  }

  /**
   * Close drawer
   */
  function close() {
    emit('update:modelValue', false)
  }

  // Watch drawer open state
  watch(
    () => props.modelValue,
    newValue => {
      if (newValue) {
        fetchAvailableGenes()
        fetchAvailableCurators()
      } else {
        resetForm()
      }
    }
  )

  // Initial load if already open
  onMounted(() => {
    if (props.modelValue) {
      fetchAvailableGenes()
      fetchAvailableCurators()
    }
  })
</script>

<style scoped>
  /* Drawer content spacing */
  .v-card-text {
    max-height: calc(100vh - 200px);
    overflow-y: auto;
  }

  /* Form sections */
  .text-subtitle-2 {
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface));
  }
</style>
