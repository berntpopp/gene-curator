<template>
  <v-navigation-drawer
    v-model="isOpen"
    location="right"
    temporary
    width="600"
    class="add-genes-drawer"
  >
    <v-card flat>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-dna</v-icon>
        Add Genes to Catalog
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="close" aria-label="Close" />
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="formValid" @submit.prevent="handleSubmit">
          <!-- Mode Selection -->
          <v-btn-toggle
            v-model="mode"
            mandatory
            color="primary"
            variant="outlined"
            class="mb-4"
            divided
          >
            <v-btn value="single">
              <v-icon start>mdi-dna</v-icon>
              Single Gene
            </v-btn>
            <v-btn value="bulk">
              <v-icon start>mdi-file-upload</v-icon>
              Bulk Import
            </v-btn>
          </v-btn-toggle>

          <!-- Single Gene Form -->
          <div v-if="mode === 'single'">
            <v-text-field
              v-model="geneData.hgnc_id"
              label="HGNC ID"
              :rules="[rules.required, rules.hgncFormat]"
              hint="e.g., HGNC:1100"
              persistent-hint
              prepend-icon="mdi-identifier"
              clearable
            />

            <v-text-field
              v-model="geneData.approved_symbol"
              label="Gene Symbol"
              :rules="[rules.required]"
              hint="e.g., BRCA1"
              persistent-hint
              prepend-icon="mdi-dna"
              clearable
            />

            <v-text-field
              v-model="geneData.approved_name"
              label="Gene Name (optional)"
              hint="Full gene name"
              persistent-hint
              prepend-icon="mdi-text"
              clearable
            />

            <v-text-field
              v-model="geneData.chromosome"
              label="Chromosome (optional)"
              hint="e.g., 17, X, Y, MT"
              persistent-hint
              prepend-icon="mdi-dna"
              clearable
            />

            <v-text-field
              v-model="geneData.location"
              label="Chromosomal Location (optional)"
              hint="e.g., 17q21.31"
              persistent-hint
              prepend-icon="mdi-map-marker"
              clearable
            />

            <v-alert type="info" variant="tonal" class="mt-4">
              <v-icon start>mdi-information</v-icon>
              Enter HGNC-approved gene information. You can verify genes at
              <a href="https://www.genenames.org/" target="_blank" class="text-white">genenames.org</a>
            </v-alert>
          </div>

          <!-- Bulk Import Form -->
          <div v-else-if="mode === 'bulk'">
            <v-textarea
              v-model="bulkInput"
              label="Gene List"
              :rules="[rules.required]"
              hint="Enter HGNC IDs or gene symbols, one per line"
              persistent-hint
              rows="10"
              prepend-icon="mdi-format-list-bulleted"
              clearable
            >
              <template #prepend-inner>
                <v-icon>mdi-format-list-bulleted</v-icon>
              </template>
            </v-textarea>

            <v-switch
              v-model="bulkOptions.skip_duplicates"
              label="Skip Duplicates"
              color="primary"
              hint="Skip genes that already exist in the catalog"
              persistent-hint
            />

            <v-alert type="info" variant="tonal" class="mt-4">
              <div class="text-subtitle-2 mb-2">Supported Formats:</div>
              <ul>
                <li><strong>HGNC IDs:</strong> HGNC:1100, HGNC:1101, ...</li>
                <li><strong>Gene Symbols:</strong> BRCA1, BRCA2, TP53, ...</li>
                <li><strong>Tab-separated:</strong> HGNC:1100\tBRCA1\t17q21.31</li>
              </ul>
            </v-alert>
          </div>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-btn variant="outlined" @click="close">
          Cancel
        </v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          :disabled="!formValid || loading"
          :loading="loading"
          @click="handleSubmit"
        >
          <v-icon start>mdi-plus</v-icon>
          {{ mode === 'single' ? 'Add Gene' : `Add ${parsedGenesCount} Genes` }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-navigation-drawer>
</template>

<script setup>
  /**
   * AddGenesDrawer Component
   *
   * Allows adding genes to the gene catalog (NOT assignment - see AssignGenesDrawer).
   * Supports both single gene entry and bulk import.
   *
   * Features:
   * - Single gene form with HGNC ID, symbol, name, location
   * - Bulk import via text list (HGNC IDs or symbols)
   * - Input validation
   * - Skip duplicates option for bulk import
   *
   * Emits:
   * - @added: When genes are successfully added
   *
   * @example
   * <AddGenesDrawer v-model="showDrawer" @added="handleGenesAdded" />
   */

  import { ref, computed, watch } from 'vue'
  import { genesAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import { useNotificationsStore } from '@/stores/notifications'

  const props = defineProps({
    modelValue: {
      type: Boolean,
      default: false
    }
  })

  const emit = defineEmits(['update:modelValue', 'added'])

  const logger = useLogger()
  const notificationStore = useNotificationsStore()

  // State
  const formRef = ref(null)
  const formValid = ref(false)
  const loading = ref(false)
  const mode = ref('single')

  // Single gene data
  const geneData = ref({
    hgnc_id: '',
    approved_symbol: '',
    approved_name: '',
    chromosome: '',
    location: ''
  })

  // Bulk import data
  const bulkInput = ref('')
  const bulkOptions = ref({
    skip_duplicates: true
  })

  // Computed
  const isOpen = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  const parsedGenesCount = computed(() => {
    if (!bulkInput.value) return 0
    return bulkInput.value.split('\n').filter(line => line.trim()).length
  })

  // Validation rules
  const rules = {
    required: v => !!v || 'This field is required',
    hgncFormat: v => {
      if (!v) return true
      return /^HGNC:\d+$/.test(v) || 'Must be in format HGNC:#### (e.g., HGNC:1100)'
    }
  }

  // Methods
  function close() {
    isOpen.value = false
    resetForm()
  }

  function resetForm() {
    geneData.value = {
      hgnc_id: '',
      approved_symbol: '',
      approved_name: '',
      chromosome: '',
      location: ''
    }
    bulkInput.value = ''
    formValid.value = false
    if (formRef.value) {
      formRef.value.resetValidation()
    }
  }

  async function handleSubmit() {
    if (!formValid.value) return

    loading.value = true

    try {
      if (mode.value === 'single') {
        await addSingleGene()
      } else {
        await addBulkGenes()
      }

      emit('added')
      close()
    } catch (error) {
      logger.error('Failed to add genes', { error: error.message, mode: mode.value })
      notificationStore.addToast(
        `Failed to add gene(s): ${error.response?.data?.detail || error.message}`,
        'error'
      )
    } finally {
      loading.value = false
    }
  }

  async function addSingleGene() {
    // Clean up data - remove empty optional fields
    const cleanData = {
      hgnc_id: geneData.value.hgnc_id.trim(),
      approved_symbol: geneData.value.approved_symbol.trim(),
      ...(geneData.value.approved_name && { approved_name: geneData.value.approved_name.trim() }),
      ...(geneData.value.chromosome && { chromosome: geneData.value.chromosome.trim() }),
      ...(geneData.value.location && { location: geneData.value.location.trim() })
    }

    logger.debug('Adding single gene', { gene_data: cleanData })

    const result = await genesAPI.createGene(cleanData)

    logger.info('Gene added successfully', {
      gene_id: result.id,
      hgnc_id: result.hgnc_id,
      symbol: result.approved_symbol
    })

    notificationStore.addToast(
      `Gene ${result.approved_symbol} added successfully`,
      'success'
    )
  }

  async function addBulkGenes() {
    const lines = bulkInput.value.split('\n').filter(line => line.trim())
    const genes = []

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue

      // Try to parse as tab-separated
      const parts = trimmed.split('\t').map(p => p.trim())

      if (parts.length >= 2) {
        // Format: HGNC_ID\tSYMBOL\t[LOCATION]
        genes.push({
          hgnc_id: parts[0],
          approved_symbol: parts[1],
          ...(parts[2] && { location: parts[2] })
        })
      } else if (trimmed.startsWith('HGNC:')) {
        // Just HGNC ID - use as both ID and symbol for now
        genes.push({
          hgnc_id: trimmed,
          approved_symbol: trimmed.replace('HGNC:', 'GENE')
        })
      } else {
        // Assume it's a gene symbol
        genes.push({
          hgnc_id: `HGNC:${Math.floor(Math.random() * 100000)}`, // Temp ID
          approved_symbol: trimmed
        })
      }
    }

    logger.debug('Adding bulk genes', { count: genes.length, skip_duplicates: bulkOptions.value.skip_duplicates })

    const result = await genesAPI.bulkCreateGenes({
      genes,
      skip_duplicates: bulkOptions.value.skip_duplicates
    })

    logger.info('Bulk genes added', {
      created: result.created,
      skipped: result.skipped,
      failed: result.failed
    })

    notificationStore.addToast(
      `Added ${result.created} genes (${result.skipped} skipped, ${result.failed} failed)`,
      result.failed > 0 ? 'warning' : 'success'
    )
  }

  // Watch for dialog open
  watch(() => props.modelValue, (newVal) => {
    if (newVal) {
      logger.debug('AddGenesDrawer opened')
    }
  })
</script>

<style scoped>
  .add-genes-drawer .v-text-field,
  .add-genes-drawer .v-textarea {
    margin-bottom: 16px;
  }

  .add-genes-drawer a {
    text-decoration: underline;
  }
</style>
