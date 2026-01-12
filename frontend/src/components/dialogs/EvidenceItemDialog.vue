<template>
  <v-dialog
    :model-value="modelValue"
    max-width="700"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>{{ getTypeIcon(evidenceType) }}</v-icon>
        {{ isEditing ? 'Edit' : 'Add' }} {{ formatType(evidenceType) }} Evidence
        <v-spacer />
        <v-btn icon variant="text" aria-label="Close" @click="handleCancel">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider />

      <v-card-text>
        <v-form ref="formRef">
          <!-- Evidence Category -->
          <v-select
            v-model="localEvidence.evidence_category"
            label="Evidence Category"
            :items="categoryOptions"
            item-title="text"
            item-value="value"
            variant="outlined"
            :rules="[v => !!v || 'Category is required']"
            required
          />

          <!-- Description -->
          <v-textarea
            v-model="localEvidence.description"
            label="Evidence Description"
            hint="Describe the evidence and its relevance"
            variant="outlined"
            rows="4"
            auto-grow
            :rules="[v => !!v || 'Description is required']"
            required
            class="mt-3"
          />

          <!-- PMIDs -->
          <PMIDInput
            v-model="localEvidence.pmids"
            label="PubMed IDs"
            hint="Enter PubMed IDs supporting this evidence"
            class="mt-3"
          />

          <!-- Computed Score -->
          <v-text-field
            v-model.number="localEvidence.computed_score"
            label="Evidence Score (Points)"
            type="number"
            step="0.1"
            min="0"
            :max="getMaxScore(evidenceType)"
            variant="outlined"
            :hint="`Maximum ${getMaxScore(evidenceType)} points for ${formatType(evidenceType)} evidence`"
            persistent-hint
            :rules="[
              v => (v !== null && v !== undefined) || 'Score is required',
              v => v >= 0 || 'Score must be positive',
              v => v <= getMaxScore(evidenceType) || `Max ${getMaxScore(evidenceType)} points`
            ]"
            class="mt-3"
          />

          <!-- Optional Metadata (expandable) -->
          <v-expansion-panels class="mt-4">
            <v-expansion-panel>
              <v-expansion-panel-title> Additional Metadata (Optional) </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row>
                  <v-col cols="12" md="4">
                    <v-text-field
                      v-model.number="localEvidence.metadata.variant_count"
                      label="Variant Count"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field
                      v-model.number="localEvidence.metadata.family_count"
                      label="Family Count"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field
                      v-model.number="localEvidence.metadata.proband_count"
                      label="Proband Count"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-form>
      </v-card-text>

      <v-divider />

      <v-card-actions class="px-4 py-3">
        <v-btn variant="outlined" @click="handleCancel">Cancel</v-btn>
        <v-spacer />
        <v-btn color="primary" @click="handleSave">
          <v-icon start>mdi-check</v-icon>
          {{ isEditing ? 'Update' : 'Add' }} Evidence
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
  /**
   * EvidenceItemDialog Component
   *
   * Dialog for adding or editing evidence items in CurationForm.
   * Provides category selection, description, PMIDs, and score input.
   *
   * @example
   * <EvidenceItemDialog
   *   v-model="showDialog"
   *   :evidence="evidenceItem"
   *   :evidence-type="'genetic'"
   *   @save="handleSave"
   * />
   */

  import { ref, computed, watch } from 'vue'
  import PMIDInput from '@/components/evidence/PMIDInput.vue'

  const props = defineProps({
    modelValue: {
      type: Boolean,
      required: true
    },
    evidence: {
      type: Object,
      default: null
    },
    evidenceType: {
      type: String,
      required: true,
      validator: value => ['genetic', 'experimental', 'contradictory'].includes(value)
    }
  })

  const emit = defineEmits(['update:modelValue', 'save'])

  const formRef = ref(null)
  const localEvidence = ref({
    evidence_type: props.evidenceType,
    evidence_category: '',
    description: '',
    pmids: [],
    computed_score: 0,
    metadata: {
      variant_count: null,
      family_count: null,
      proband_count: null
    }
  })

  const isEditing = computed(() => !!props.evidence)

  // Watch for evidence changes (when editing)
  watch(
    () => props.evidence,
    newEvidence => {
      if (newEvidence) {
        localEvidence.value = {
          ...newEvidence,
          metadata: newEvidence.metadata || {
            variant_count: null,
            family_count: null,
            proband_count: null
          }
        }
      } else {
        resetForm()
      }
    },
    { immediate: true }
  )

  /**
   * Category options based on evidence type
   */
  const categoryOptions = computed(() => {
    if (props.evidenceType === 'genetic') {
      return [
        { text: 'Case-Level', value: 'case_level' },
        { text: 'Segregation', value: 'segregation' },
        { text: 'Case-Control', value: 'case_control' }
      ]
    } else if (props.evidenceType === 'experimental') {
      return [
        { text: 'Expression', value: 'expression' },
        { text: 'Protein Function', value: 'protein_function' },
        { text: 'Models', value: 'models' },
        { text: 'Rescue', value: 'rescue' }
      ]
    } else if (props.evidenceType === 'contradictory') {
      return [{ text: 'Contradictory Evidence', value: 'contradictory' }]
    }
    return []
  })

  /**
   * Get icon for evidence type
   */
  function getTypeIcon(type) {
    const icons = {
      genetic: 'mdi-dna',
      experimental: 'mdi-flask',
      contradictory: 'mdi-alert'
    }
    return icons[type] || 'mdi-file-document'
  }

  /**
   * Format evidence type for display
   */
  function formatType(type) {
    return type.charAt(0).toUpperCase() + type.slice(1)
  }

  /**
   * Get maximum score for evidence type
   */
  function getMaxScore(type) {
    return type === 'genetic' ? 12 : 6
  }

  /**
   * Reset form to initial state
   */
  function resetForm() {
    localEvidence.value = {
      evidence_type: props.evidenceType,
      evidence_category: '',
      description: '',
      pmids: [],
      computed_score: 0,
      metadata: {
        variant_count: null,
        family_count: null,
        proband_count: null
      }
    }
    if (formRef.value) {
      formRef.value.resetValidation()
    }
  }

  /**
   * Handle save
   */
  async function handleSave() {
    const { valid } = await formRef.value.validate()
    if (!valid) return

    // Clean up metadata (remove null values)
    const cleanedMetadata = {}
    if (localEvidence.value.metadata) {
      Object.entries(localEvidence.value.metadata).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          cleanedMetadata[key] = value
        }
      })
    }

    const evidenceToSave = {
      ...localEvidence.value,
      metadata: Object.keys(cleanedMetadata).length > 0 ? cleanedMetadata : null
    }

    emit('save', evidenceToSave)
    resetForm()
  }

  /**
   * Handle cancel
   */
  function handleCancel() {
    resetForm()
    emit('update:modelValue', false)
  }
</script>

<style scoped>
  /* Form spacing */
  .v-card-text {
    padding-top: 20px;
    padding-bottom: 20px;
  }
</style>
