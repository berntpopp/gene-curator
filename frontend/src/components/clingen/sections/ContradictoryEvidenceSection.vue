<template>
  <div class="contradictory-evidence-section">
    <v-alert v-if="!readonly && modelValue.length === 0" type="info" variant="tonal" class="mb-4">
      <template #prepend>
        <v-icon>mdi-information</v-icon>
      </template>
      <div class="font-weight-medium">No Contradictory Evidence</div>
      <div class="text-body-2 mt-1">
        Add evidence that contradicts the gene-disease association if applicable. This may affect
        the final classification.
      </div>
    </v-alert>

    <div class="d-flex align-center mb-3">
      <span class="text-subtitle-1 font-weight-medium">Contradictory Evidence</span>
      <v-spacer />
      <v-btn v-if="!readonly" color="error" variant="tonal" size="small" @click="addEvidence">
        <v-icon start>mdi-plus</v-icon>
        Add Contradictory Evidence
      </v-btn>
    </div>

    <v-card v-if="modelValue.length > 0" variant="outlined">
      <v-table density="compact">
        <thead>
          <tr class="bg-error-lighten-5">
            <th style="width: 100px">Label</th>
            <th style="width: 100px">PMID</th>
            <th style="width: 150px">Type</th>
            <th>Description</th>
            <th style="width: 120px">Impact</th>
            <th v-if="!readonly" style="width: 60px">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in modelValue" :key="index">
            <td>
              <v-text-field
                :model-value="item.label"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                placeholder="Label"
                @update:model-value="updateField(index, 'label', $event)"
              />
            </td>
            <td>
              <div class="d-flex align-center">
                <v-text-field
                  :model-value="item.pmid"
                  density="compact"
                  variant="plain"
                  hide-details
                  :readonly="readonly"
                  placeholder="PMID"
                  @update:model-value="updateField(index, 'pmid', $event)"
                />
                <v-btn
                  v-if="item.pmid"
                  icon
                  size="x-small"
                  variant="text"
                  :href="`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}`"
                  target="_blank"
                  title="Open in PubMed"
                >
                  <v-icon size="small">mdi-open-in-new</v-icon>
                </v-btn>
              </div>
            </td>
            <td>
              <v-select
                :model-value="item.evidence_type"
                :items="evidenceTypes"
                item-title="label"
                item-value="value"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="updateField(index, 'evidence_type', $event)"
              />
            </td>
            <td>
              <v-text-field
                :model-value="item.description"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                placeholder="Description of contradictory evidence"
                @update:model-value="updateField(index, 'description', $event)"
              />
            </td>
            <td>
              <v-select
                :model-value="item.impact"
                :items="impactOptions"
                item-title="label"
                item-value="value"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="updateField(index, 'impact', $event)"
              />
            </td>
            <td v-if="!readonly">
              <v-btn icon size="small" color="error" variant="text" @click="removeEvidence(index)">
                <v-icon size="small">mdi-delete</v-icon>
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <v-alert v-if="modelValue.length > 0" type="warning" variant="tonal" class="mt-4">
      <template #prepend>
        <v-icon>mdi-alert</v-icon>
      </template>
      <div class="font-weight-medium">Classification Impact</div>
      <div class="text-body-2 mt-1">
        The presence of contradictory evidence may result in a "Disputed" classification, regardless
        of the total score. Expert review is recommended.
      </div>
    </v-alert>
  </div>
</template>

<script setup>
  /**
   * ContradictoryEvidenceSection
   *
   * Handles contradictory evidence that may lead to "Disputed" classification.
   */

  const props = defineProps({
    modelValue: {
      type: Array,
      default: () => []
    },
    readonly: {
      type: Boolean,
      default: false
    }
  })

  const emit = defineEmits(['update:model-value'])

  const evidenceTypes = [
    { value: 'population', label: 'Population/control data' },
    { value: 'segregation', label: 'Non-segregation' },
    { value: 'functional', label: 'Contradictory functional data' },
    { value: 'phenotype', label: 'Phenotype mismatch' },
    { value: 'other', label: 'Other' }
  ]

  const impactOptions = [
    { value: 'disputed', label: 'Disputed' },
    { value: 'note', label: 'Note only' },
    { value: 'requires_review', label: 'Review needed' }
  ]

  function addEvidence() {
    const items = [...props.modelValue]
    items.push({
      label: '',
      pmid: '',
      evidence_type: 'population',
      description: '',
      impact: 'note',
      explanation: ''
    })
    emit('update:model-value', items)
  }

  function updateField(index, key, value) {
    const items = [...props.modelValue]
    items[index] = { ...items[index], [key]: value }
    emit('update:model-value', items)
  }

  function removeEvidence(index) {
    const items = [...props.modelValue]
    items.splice(index, 1)
    emit('update:model-value', items)
  }
</script>

<style scoped>
  .contradictory-evidence-section :deep(.bg-error-lighten-5) {
    background: rgba(var(--v-theme-error), 0.05) !important;
  }

  .contradictory-evidence-section :deep(td) {
    padding: 4px 8px !important;
    vertical-align: middle;
  }
</style>
