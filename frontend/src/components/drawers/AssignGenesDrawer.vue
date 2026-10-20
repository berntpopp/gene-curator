<template>
  <v-navigation-drawer
    :model-value="modelValue"
    location="right"
    temporary
    width="500"
    class="assign-genes-drawer"
    @update:model-value="emit('update:modelValue', $event)"
    @keydown.escape="close"
  >
    <div class="drawer-container">
      <!-- Header -->
      <v-toolbar density="compact" color="primary" class="drawer-header">
        <v-toolbar-title>Assign Genes to Curators</v-toolbar-title>
        <v-spacer />
        <v-btn icon aria-label="Close" @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <!-- Content -->
      <div class="drawer-content pt-4">
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
                <v-list-item-subtitle>{{ item.raw.hgnc_id }}</v-list-item-subtitle>
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
      </div>

      <!-- Actions -->
      <div class="drawer-footer">
        <v-btn variant="outlined" @click="close">Cancel</v-btn>
        <v-spacer />
        <v-btn color="primary" :loading="assigning" @click="handleAssign">
          <v-icon start>mdi-check</v-icon>
          Assign {{ selectedGenes.length > 0 ? `(${selectedGenes.length})` : '' }}
        </v-btn>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
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

  interface GeneOption {
    gene_id: string
    gene_symbol: string
    hgnc_id: string
  }

  interface CuratorOption {
    user_id: string
    email: string
    full_name?: string | null
    role: string
  }

  interface ApiError {
    message: string
  }

  const props = defineProps<{
    modelValue: boolean
    scopeId: string
  }>()

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    assigned: []
  }>()

  const scopesStore = useScopesStore()
  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // Form state
  const formRef = ref<{
    validate: () => Promise<{ valid: boolean }>
    resetValidation: () => void
  } | null>(null)
  const selectedGenes = ref<string[]>([])
  const selectedCurator = ref<string | null>(null)
  const priority = ref<string>('normal')
  const notes = ref('')

  // Loading states
  const loadingGenes = ref(false)
  const loadingCurators = ref(false)
  const assigning = ref(false)

  // Data
  const availableGenes = ref<GeneOption[]>([])
  const availableCurators = ref<CuratorOption[]>([])

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
      const { genes: allGenes } = await genesAPI.getGenes()

      // Fetch already assigned genes
      const { assignments } = await assignmentsAPI.getAssignments({ scope_id: props.scopeId })
      const assignedGeneIds = new Set(assignments.map(a => a.gene_id))

      // Filter out already assigned genes
      availableGenes.value = allGenes
        .filter(gene => !assignedGeneIds.has(gene.id))
        .map(gene => ({
          gene_id: gene.id,
          gene_symbol: gene.approved_symbol,
          hgnc_id: gene.hgnc_id
        }))

      logger.debug('Available genes loaded', {
        total: allGenes.length,
        available: availableGenes.value.length
      })
    } catch (error) {
      logger.error('Failed to fetch available genes', { error: (error as ApiError).message })
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
        .filter(member => ['curator', 'admin'].includes(member.role))
        .map(member => ({
          user_id: member.user_id,
          email: member.user_email ?? '',
          full_name: member.user_full_name,
          role: member.role
        }))

      logger.debug('Available curators loaded', { count: availableCurators.value.length })
    } catch (error) {
      logger.error('Failed to fetch curators', { error: (error as ApiError).message })
      notificationStore.addToast('Failed to load curators', 'error')
    } finally {
      loadingCurators.value = false
    }
  }

  /**
   * Get avatar color based on email hash
   */
  function getAvatarColor(email: string): string {
    const colors = ['primary', 'secondary', 'success', 'info', 'warning']
    const hash = email.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    return colors[hash % colors.length] ?? 'primary'
  }

  /**
   * Get initials from name
   */
  function getInitials(name: string): string {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .substring(0, 2)
  }

  /**
   * Get role color
   */
  function getRoleColor(role: string): string {
    const colors: Record<string, string> = {
      admin: 'error',
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
    if (!formRef.value) return
    const { valid } = await formRef.value.validate()
    if (!valid) return

    assigning.value = true
    try {
      // Create assignments for each gene
      const assignments = selectedGenes.value.map(geneId => ({
        gene_id: geneId,
        scope_id: props.scopeId,
        assigned_curator_id: selectedCurator.value,
        priority_level: priority.value,
        assignment_notes: notes.value || null
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
      logger.error('Failed to assign genes', { error: (error as ApiError).message })
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
  /* Ensure drawer doesn't overlap with page footer or header */
  .assign-genes-drawer {
    top: 64px !important; /* Below app header */
    bottom: 77px !important; /* Above page footer */
    height: calc(100vh - 64px - 77px) !important; /* Viewport minus header and footer */
  }

  /* Flex container for full-height drawer layout */
  .drawer-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  /* Fixed header */
  .drawer-header {
    flex-shrink: 0;
  }

  /* Scrollable content area */
  .drawer-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  /* Sticky footer */
  .drawer-footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding: 16px;
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    background: rgb(var(--v-theme-surface));
  }

  /* Form sections */
  .text-subtitle-2 {
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface));
  }
</style>
