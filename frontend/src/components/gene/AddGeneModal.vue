<!--
  AddGeneModal Component

  Modal dialog for adding genes to the gene catalog with HGNC search autocomplete.
  Replaces the old drawer-based approach with a cleaner modal UX.

  **Features**:
  - Two modes: Single gene search and Bulk import
  - HGNC autocomplete search by symbol, HGNC ID, or name
  - Auto-populated gene details from HGNC API
  - Bulk import with validation against HGNC
  - Clear visual feedback for validation status

  **Props**:
  - modelValue: v-model for dialog visibility
  - scopeId: Optional scope ID for context

  **Events**:
  - update:modelValue: Dialog visibility change
  - added: Emitted when gene(s) are successfully added

  @example
  <AddGeneModal
    v-model="showModal"
    :scope-id="scopeId"
    @added="handleGenesAdded"
  />
-->

<template>
  <v-dialog v-model="isOpen" max-width="700" persistent @keydown.escape="handleCancel">
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start color="primary" size="28">mdi-dna</v-icon>
        <span class="text-h6">Add Genes to Catalog</span>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" density="compact" @click="handleCancel" />
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
        <!-- Mode Selection Tabs -->
        <v-tabs v-model="mode" class="mb-4" color="primary">
          <v-tab value="single">
            <v-icon start>mdi-magnify</v-icon>
            Search Gene
          </v-tab>
          <v-tab value="bulk">
            <v-icon start>mdi-file-upload</v-icon>
            Bulk Import
          </v-tab>
        </v-tabs>

        <v-window v-model="mode">
          <!-- Single Gene Search Mode -->
          <v-window-item value="single">
            <v-form ref="singleFormRef" v-model="singleFormValid">
              <!-- Gene Search Autocomplete -->
              <v-autocomplete
                v-model="selectedGene"
                v-model:search="searchQuery"
                :items="searchResults"
                :loading="isSearching"
                item-title="symbol"
                item-value="hgnc_id"
                return-object
                label="Search for gene"
                placeholder="Type gene symbol, HGNC ID, or name..."
                prepend-inner-icon="mdi-magnify"
                clearable
                :rules="[v => !!v || 'Please select a gene']"
                :no-data-text="noDataText"
                variant="outlined"
                density="comfortable"
                hide-no-data
                @update:search="handleSearchUpdate"
              >
                <!-- Custom item template -->
                <template #item="{ props: listItemProps, item }">
                  <v-list-item v-bind="listItemProps" :title="undefined">
                    <template #prepend>
                      <v-icon color="primary" class="mr-2">mdi-dna</v-icon>
                    </template>
                    <v-list-item-title class="font-weight-bold">
                      {{ item.raw.symbol }}
                      <v-chip
                        v-if="item.raw.status === 'Approved'"
                        size="x-small"
                        color="success"
                        variant="tonal"
                        class="ml-2"
                      >
                        Approved
                      </v-chip>
                    </v-list-item-title>
                    <v-list-item-subtitle>
                      <span class="text-caption">{{ item.raw.hgnc_id }}</span>
                      <span v-if="item.raw.name" class="mx-2">|</span>
                      <span v-if="item.raw.name" class="text-caption">{{ item.raw.name }}</span>
                    </v-list-item-subtitle>
                    <v-list-item-subtitle v-if="item.raw.location" class="text-caption">
                      <v-icon size="x-small" class="mr-1">mdi-map-marker</v-icon>
                      {{ item.raw.location }}
                    </v-list-item-subtitle>
                  </v-list-item>
                </template>

                <!-- Selected gene display -->
                <template #selection="{ item }">
                  <v-chip color="primary" variant="tonal">
                    <v-icon start size="small">mdi-dna</v-icon>
                    {{ item.raw.symbol }}
                    <span class="text-caption ml-2">({{ item.raw.hgnc_id }})</span>
                  </v-chip>
                </template>

                <!-- Loading indicator -->
                <template #append-inner>
                  <v-progress-circular
                    v-if="isSearching"
                    size="20"
                    width="2"
                    indeterminate
                    color="primary"
                  />
                </template>
              </v-autocomplete>

              <!-- Selected Gene Details Preview -->
              <v-expand-transition>
                <v-card v-if="selectedGene" variant="outlined" class="mt-4 pa-4" color="success">
                  <div class="d-flex align-center mb-2">
                    <v-icon color="success" class="mr-2">mdi-check-circle</v-icon>
                    <span class="text-subtitle-1 font-weight-bold">Gene Details (from HGNC)</span>
                  </div>

                  <v-row dense>
                    <v-col cols="6">
                      <div class="text-caption text-medium-emphasis">HGNC ID</div>
                      <div class="font-weight-medium">{{ selectedGene.hgnc_id }}</div>
                    </v-col>
                    <v-col cols="6">
                      <div class="text-caption text-medium-emphasis">Symbol</div>
                      <div class="font-weight-medium">{{ selectedGene.symbol }}</div>
                    </v-col>
                    <v-col v-if="selectedGene.name" cols="12">
                      <div class="text-caption text-medium-emphasis">Name</div>
                      <div class="font-weight-medium">{{ selectedGene.name }}</div>
                    </v-col>
                    <v-col v-if="selectedGene.location" cols="6">
                      <div class="text-caption text-medium-emphasis">Location</div>
                      <div class="font-weight-medium">{{ selectedGene.location }}</div>
                    </v-col>
                    <v-col v-if="selectedGene.chromosome" cols="6">
                      <div class="text-caption text-medium-emphasis">Chromosome</div>
                      <div class="font-weight-medium">{{ selectedGene.chromosome }}</div>
                    </v-col>
                    <v-col v-if="selectedGene.alias_symbols?.length" cols="12">
                      <div class="text-caption text-medium-emphasis">Aliases</div>
                      <div>
                        <v-chip
                          v-for="alias in selectedGene.alias_symbols.slice(0, 5)"
                          :key="alias"
                          size="x-small"
                          variant="outlined"
                          class="mr-1 mb-1"
                        >
                          {{ alias }}
                        </v-chip>
                        <span
                          v-if="selectedGene.alias_symbols.length > 5"
                          class="text-caption text-medium-emphasis"
                        >
                          +{{ selectedGene.alias_symbols.length - 5 }} more
                        </span>
                      </div>
                    </v-col>
                  </v-row>
                </v-card>
              </v-expand-transition>

              <v-alert type="info" variant="tonal" density="compact" class="mt-4">
                <v-icon start size="small">mdi-information</v-icon>
                Search uses the official HGNC database. Gene details are automatically populated.
              </v-alert>
            </v-form>
          </v-window-item>

          <!-- Bulk Import Mode -->
          <v-window-item value="bulk">
            <v-form ref="bulkFormRef" v-model="bulkFormValid">
              <v-textarea
                v-model="bulkInput"
                label="Gene List"
                :rules="[v => !!v || 'Please enter at least one gene']"
                hint="Enter gene symbols or HGNC IDs, one per line or comma-separated"
                persistent-hint
                rows="6"
                variant="outlined"
                placeholder="BRCA1&#10;BRCA2&#10;TP53&#10;or: HGNC:1100, HGNC:1101"
                clearable
                :disabled="isValidatingBulk"
              />

              <div class="d-flex align-center mt-3 mb-2">
                <v-btn
                  color="primary"
                  variant="tonal"
                  :loading="isValidatingBulk"
                  :disabled="!bulkInput?.trim()"
                  @click="validateBulkGenes"
                >
                  <v-icon start>mdi-check-all</v-icon>
                  Validate Genes
                </v-btn>
                <v-spacer />
                <v-switch
                  v-model="skipDuplicates"
                  label="Skip existing genes"
                  color="primary"
                  density="compact"
                  hide-details
                />
              </div>

              <!-- Validation Results -->
              <v-expand-transition>
                <div v-if="bulkValidationResults.length > 0" class="mt-3">
                  <v-alert
                    :type="bulkValidationSummary.invalid > 0 ? 'warning' : 'success'"
                    variant="tonal"
                    density="compact"
                    class="mb-3"
                  >
                    <div class="d-flex align-center">
                      <v-icon start>{{
                        bulkValidationSummary.invalid > 0 ? 'mdi-alert-circle' : 'mdi-check-circle'
                      }}</v-icon>
                      <span>
                        {{ bulkValidationSummary.valid }} valid,
                        {{ bulkValidationSummary.invalid }} invalid,
                        {{ bulkValidationSummary.suggestions }} with suggestions
                      </span>
                    </div>
                  </v-alert>

                  <v-list density="compact" class="validation-results-list">
                    <v-list-item
                      v-for="(result, idx) in bulkValidationResults"
                      :key="idx"
                      :class="getValidationClass(result.status)"
                    >
                      <template #prepend>
                        <v-icon :color="getValidationColor(result.status)" size="small">
                          {{ getValidationIcon(result.status) }}
                        </v-icon>
                      </template>
                      <v-list-item-title class="text-body-2">
                        <span class="font-weight-medium">{{ result.input }}</span>
                        <span v-if="result.gene" class="text-medium-emphasis">
                          <v-icon size="x-small" class="mx-1">mdi-arrow-right</v-icon>
                          {{ result.gene.symbol }} ({{ result.gene.hgnc_id }})
                        </span>
                      </v-list-item-title>
                      <v-list-item-subtitle v-if="result.message" class="text-caption">
                        {{ result.message }}
                      </v-list-item-subtitle>
                      <template #append>
                        <div
                          v-if="result.status === 'suggestion' && result.gene"
                          class="d-flex align-center ga-1"
                        >
                          <v-btn
                            size="x-small"
                            variant="tonal"
                            color="primary"
                            @click="acceptSuggestion(idx)"
                          >
                            Accept
                          </v-btn>
                          <v-menu v-if="result.alternatives?.length > 0">
                            <template #activator="{ props: menuProps }">
                              <v-btn
                                v-bind="menuProps"
                                size="x-small"
                                variant="outlined"
                                color="secondary"
                              >
                                <v-icon size="small">mdi-chevron-down</v-icon>
                                Others
                              </v-btn>
                            </template>
                            <v-list density="compact">
                              <v-list-subheader>Select correct gene</v-list-subheader>
                              <v-list-item
                                v-for="(alt, altIdx) in result.alternatives"
                                :key="altIdx"
                                @click="selectAlternative(idx, alt)"
                              >
                                <v-list-item-title class="text-body-2">
                                  <strong>{{ alt.symbol }}</strong>
                                  <span class="text-medium-emphasis ml-2">{{ alt.hgnc_id }}</span>
                                </v-list-item-title>
                                <v-list-item-subtitle
                                  v-if="alt.name"
                                  class="text-caption text-truncate"
                                  style="max-width: 250px"
                                >
                                  {{ alt.name }}
                                </v-list-item-subtitle>
                              </v-list-item>
                            </v-list>
                          </v-menu>
                        </div>
                      </template>
                    </v-list-item>
                  </v-list>
                </div>
              </v-expand-transition>
            </v-form>
          </v-window-item>
        </v-window>
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
          :loading="isSubmitting"
          @click="handleSubmit"
        >
          <v-icon start>mdi-plus</v-icon>
          {{ submitButtonText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
  import { ref, computed, watch } from 'vue'
  import { useHgncSearch } from '@/composables/useHgncSearch'
  import { genesAPI, assignmentsAPI } from '@/api'
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
      default: null
    }
  })

  const emit = defineEmits(['update:modelValue', 'added'])

  // ============================================
  // COMPOSABLES & STORES
  // ============================================

  const logger = useLogger()
  const notificationStore = useNotificationsStore()
  const { results: searchResults, isSearching, search, validateBulk } = useHgncSearch()

  // ============================================
  // STATE
  // ============================================

  // Form refs
  const singleFormRef = ref(null)
  const bulkFormRef = ref(null)
  const singleFormValid = ref(false)
  const bulkFormValid = ref(false)

  // Mode and loading
  const mode = ref('single')
  const isSubmitting = ref(false)
  const isValidatingBulk = ref(false)

  // Single gene mode
  const searchQuery = ref('')
  const selectedGene = ref(null)

  // Bulk mode
  const bulkInput = ref('')
  const skipDuplicates = ref(true)
  const bulkValidationResults = ref([])

  // ============================================
  // COMPUTED
  // ============================================

  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  const noDataText = computed(() => {
    if (isSearching.value) return 'Searching...'
    if (searchQuery.value?.length < 2) return 'Type at least 2 characters to search'
    return 'No genes found'
  })

  const bulkValidationSummary = computed(() => {
    const valid = bulkValidationResults.value.filter(r => r.status === 'valid').length
    const invalid = bulkValidationResults.value.filter(r => r.status === 'not_found').length
    const suggestions = bulkValidationResults.value.filter(r => r.status === 'suggestion').length
    return { valid, invalid, suggestions }
  })

  const canSubmit = computed(() => {
    if (mode.value === 'single') {
      return !!selectedGene.value
    }
    // For bulk, require validation and at least one valid gene
    return (
      bulkValidationResults.value.length > 0 &&
      bulkValidationSummary.value.valid + bulkValidationSummary.value.suggestions > 0
    )
  })

  const submitButtonText = computed(() => {
    if (mode.value === 'single') {
      return 'Add Gene'
    }
    const count = bulkValidationSummary.value.valid + bulkValidationSummary.value.suggestions
    return `Add ${count} Gene${count !== 1 ? 's' : ''}`
  })

  // ============================================
  // METHODS
  // ============================================

  /**
   * Handle search input changes
   */
  const handleSearchUpdate = async query => {
    if (query && query.length >= 2) {
      await search(query)
    }
  }

  /**
   * Validate bulk gene input
   */
  const validateBulkGenes = async () => {
    if (!bulkInput.value?.trim()) return

    isValidatingBulk.value = true
    bulkValidationResults.value = []

    try {
      // Parse input - split by newline or comma
      const identifiers = bulkInput.value
        .split(/[\n,]/)
        .map(s => s.trim())
        .filter(s => s.length > 0)

      logger.debug('Validating bulk genes', { count: identifiers.length })

      const result = await validateBulk(identifiers)
      bulkValidationResults.value = result.results

      logger.info('Bulk validation completed', {
        valid: result.valid.length,
        invalid: result.invalid.length
      })
    } catch (error) {
      logger.error('Bulk validation error', { error: error.message })
      notificationStore.addToast('Failed to validate genes', 'error')
    } finally {
      isValidatingBulk.value = false
    }
  }

  /**
   * Accept a suggestion in bulk validation
   */
  const acceptSuggestion = idx => {
    if (bulkValidationResults.value[idx]) {
      bulkValidationResults.value[idx].status = 'valid'
    }
  }

  /**
   * Select an alternative gene for a suggestion
   */
  const selectAlternative = (idx, alternative) => {
    if (bulkValidationResults.value[idx]) {
      bulkValidationResults.value[idx].gene = alternative
      bulkValidationResults.value[idx].status = 'valid'
      bulkValidationResults.value[idx].message = null
    }
  }

  /**
   * Get validation status CSS class
   */
  const getValidationClass = status => {
    switch (status) {
      case 'valid':
        return 'bg-success-lighten-5'
      case 'suggestion':
        return 'bg-warning-lighten-5'
      case 'not_found':
        return 'bg-error-lighten-5'
      default:
        return ''
    }
  }

  /**
   * Get validation status color
   */
  const getValidationColor = status => {
    switch (status) {
      case 'valid':
        return 'success'
      case 'suggestion':
        return 'warning'
      case 'not_found':
        return 'error'
      default:
        return 'grey'
    }
  }

  /**
   * Get validation status icon
   */
  const getValidationIcon = status => {
    switch (status) {
      case 'valid':
        return 'mdi-check-circle'
      case 'suggestion':
        return 'mdi-help-circle'
      case 'not_found':
        return 'mdi-close-circle'
      default:
        return 'mdi-circle-outline'
    }
  }

  /**
   * Reset form state
   */
  const resetForm = () => {
    mode.value = 'single'
    searchQuery.value = ''
    selectedGene.value = null
    bulkInput.value = ''
    bulkValidationResults.value = []
    skipDuplicates.value = true
    singleFormValid.value = false
    bulkFormValid.value = false
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

    isSubmitting.value = true

    try {
      if (mode.value === 'single') {
        await addSingleGene()
      } else {
        await addBulkGenes()
      }

      emit('added')
      resetForm()
      isOpen.value = false
    } catch (error) {
      logger.error('Failed to add genes', { error: error.message, mode: mode.value })
      notificationStore.addToast(
        `Failed to add gene(s): ${error.response?.data?.detail || error.message}`,
        'error'
      )
    } finally {
      isSubmitting.value = false
    }
  }

  /**
   * Add single gene
   */
  const addSingleGene = async () => {
    const geneData = {
      hgnc_id: selectedGene.value.hgnc_id,
      approved_symbol: selectedGene.value.symbol,
      chromosome: selectedGene.value.chromosome || undefined,
      location: selectedGene.value.location || undefined,
      previous_symbols: selectedGene.value.previous_symbols || undefined,
      alias_symbols: selectedGene.value.alias_symbols || undefined,
      details: selectedGene.value.name ? { approved_name: selectedGene.value.name } : undefined
    }

    logger.debug('Adding single gene', { gene_data: geneData })

    const result = await genesAPI.createGene(geneData)

    logger.info('Gene added successfully', {
      gene_id: result.id,
      hgnc_id: result.hgnc_id,
      symbol: result.approved_symbol
    })

    // If scopeId is provided, also assign the gene to the scope (unassigned status)
    if (props.scopeId) {
      try {
        await assignmentsAPI.createAssignment({
          gene_id: result.id,
          scope_id: props.scopeId,
          assigned_curator_id: null, // Unassigned
          priority_level: 'medium'
        })
        logger.info('Gene assigned to scope', {
          gene_id: result.id,
          scope_id: props.scopeId
        })
        notificationStore.addToast(
          `Gene ${result.approved_symbol} added and assigned to scope`,
          'success'
        )
      } catch (assignError) {
        // Gene was added but assignment failed - still report success for gene creation
        logger.warn('Gene added but scope assignment failed', {
          gene_id: result.id,
          scope_id: props.scopeId,
          error: assignError.message
        })
        notificationStore.addToast(
          `Gene ${result.approved_symbol} added (assignment failed: ${assignError.response?.data?.detail || assignError.message})`,
          'warning'
        )
      }
    } else {
      notificationStore.addToast(`Gene ${result.approved_symbol} added successfully`, 'success')
    }
  }

  /**
   * Add bulk genes
   */
  const addBulkGenes = async () => {
    // Get valid genes (valid status or accepted suggestions)
    const genesToAdd = bulkValidationResults.value
      .filter(r => r.status === 'valid' && r.gene)
      .map(r => ({
        hgnc_id: r.gene.hgnc_id,
        approved_symbol: r.gene.symbol,
        chromosome: r.gene.chromosome || undefined,
        location: r.gene.location || undefined,
        details: r.gene.name ? { approved_name: r.gene.name } : undefined
      }))

    if (genesToAdd.length === 0) {
      notificationStore.addToast('No valid genes to add', 'warning')
      return
    }

    logger.debug('Adding bulk genes', {
      count: genesToAdd.length,
      skip_duplicates: skipDuplicates.value
    })

    const result = await genesAPI.bulkCreateGenes({
      genes: genesToAdd,
      skip_duplicates: skipDuplicates.value
    })

    logger.info('Bulk genes added', {
      created: result.total_created,
      skipped: result.total_skipped,
      failed: result.total_errors
    })

    // If scopeId is provided and genes were created, assign them to the scope
    if (props.scopeId && result.created_genes && result.created_genes.length > 0) {
      try {
        const geneIds = result.created_genes.map(g => g.id)
        await assignmentsAPI.bulkAssignGenes({
          gene_ids: geneIds,
          scope_id: props.scopeId,
          assigned_curator_id: null // Unassigned
        })
        logger.info('Bulk genes assigned to scope', {
          gene_count: geneIds.length,
          scope_id: props.scopeId
        })
        notificationStore.addToast(
          `Added and assigned ${result.total_created} genes (${result.total_skipped} skipped, ${result.total_errors} failed)`,
          result.total_errors > 0 ? 'warning' : 'success'
        )
      } catch (assignError) {
        logger.warn('Genes added but scope assignment failed', {
          gene_count: result.created_genes.length,
          scope_id: props.scopeId,
          error: assignError.message
        })
        notificationStore.addToast(
          `Added ${result.total_created} genes but scope assignment failed: ${assignError.response?.data?.detail || assignError.message}`,
          'warning'
        )
      }
    } else {
      notificationStore.addToast(
        `Added ${result.total_created} genes (${result.total_skipped} skipped, ${result.total_errors} failed)`,
        result.total_errors > 0 ? 'warning' : 'success'
      )
    }
  }

  // ============================================
  // WATCHERS
  // ============================================

  // Reset form when dialog opens
  watch(isOpen, newValue => {
    if (newValue) {
      resetForm()
      logger.debug('AddGeneModal opened')
    }
  })

  // Clear validation results when bulk input changes significantly
  watch(bulkInput, () => {
    if (bulkValidationResults.value.length > 0) {
      bulkValidationResults.value = []
    }
  })
</script>

<style scoped>
  .validation-results-list {
    max-height: 250px;
    overflow-y: auto;
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 4px;
  }

  .bg-success-lighten-5 {
    background-color: rgba(var(--v-theme-success), 0.05);
  }

  .bg-warning-lighten-5 {
    background-color: rgba(var(--v-theme-warning), 0.05);
  }

  .bg-error-lighten-5 {
    background-color: rgba(var(--v-theme-error), 0.05);
  }
</style>
